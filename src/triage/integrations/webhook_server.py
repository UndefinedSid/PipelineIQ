"""FastAPI webhook server for automated organization-wide CI triage."""

import hashlib
import hmac
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from triage.config import settings
from triage.engine import TriageEngine
from triage.integrations.github_client import GitHubTriageClient
from triage.integrations.slack_client import post_to_slack

logger = logging.getLogger("triage.server")
app = FastAPI(title="AI CI/CD Failure Triage Webhook Server", version="1.0.0")
engine = TriageEngine()


def verify_github_signature(payload_bytes: bytes, signature_header: str, secret: str):
    """Verifies HMAC SHA-256 signature from GitHub Webhooks."""
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Invalid signature header format")

    expected = "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Webhook signature mismatch")


async def process_failed_workflow_run(payload: Dict[str, Any]):
    """Background task to fetch logs, perform triage, and post results."""
    workflow_run = payload.get("workflow_run", {})
    conclusion = workflow_run.get("conclusion")

    if conclusion != "failure":
        return

    repo_data = payload.get("repository", {})
    repo_name = repo_data.get("full_name")
    run_id = workflow_run.get("id")
    pull_requests = workflow_run.get("pull_requests", [])

    logger.info(f"Processing failure for repo '{repo_name}', run ID {run_id}")

    try:
        gh_client = GitHubTriageClient()
        raw_log = await gh_client.fetch_workflow_run_logs(repo_name, run_id)
        report = await engine.triage_log(
            raw_log=raw_log,
            failed_step_hint=workflow_run.get("name", "Workflow Run")
        )

        # Post to Pull Request if available
        if pull_requests:
            pr_number = pull_requests[0].get("number")
            gh_client.post_or_update_pr_comment(repo_name, pr_number, report)

        # Dispatch Slack notification
        pr_html_url = pull_requests[0].get("html_url", "") if pull_requests else ""
        await post_to_slack(report, repo_name=repo_name, pr_url=pr_html_url)

    except Exception as e:
        logger.error(f"Error triaging workflow run {run_id}: {e}", exc_info=True)


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256")
):
    body_bytes = await request.body()

    if settings.GITHUB_WEBHOOK_SECRET:
        verify_github_signature(body_bytes, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET)

    if x_github_event == "workflow_run":
        payload = await request.json()
        if payload.get("action") == "completed" and payload.get("workflow_run", {}).get("conclusion") == "failure":
            background_tasks.add_task(process_failed_workflow_run, payload)
            return {"status": "queued", "message": "Failure triage job enqueued"}

    return {"status": "ignored", "event": x_github_event}
