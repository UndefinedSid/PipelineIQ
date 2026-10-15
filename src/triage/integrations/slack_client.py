"""Slack webhook client for dispatching Block Kit triage cards."""

import logging
from typing import Optional
import httpx
from triage.config import settings
from triage.models import TriageReport
from triage.formatters.slack import format_slack_block_kit

logger = logging.getLogger("triage.slack")


async def post_to_slack(
    report: TriageReport,
    webhook_url: Optional[str] = None,
    repo_name: str = "repository",
    pr_url: str = ""
) -> bool:
    """Posts a rich Block Kit notification to a Slack incoming webhook."""
    target_url = webhook_url or settings.SLACK_WEBHOOK_URL
    if not target_url:
        logger.debug("No Slack webhook configured. Skipping Slack notification.")
        return False

    payload = format_slack_block_kit(report, repo_name=repo_name, pr_url=pr_url)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(target_url, json=payload)
            resp.raise_for_status()
            logger.info("Successfully posted triage report to Slack")
            return True
        except Exception as e:
            logger.error(f"Failed to post triage notification to Slack: {e}")
            return False
