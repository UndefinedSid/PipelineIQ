"""GitHub API client for workflow logs and PR comments."""

import io
import logging
import zipfile
from typing import Optional
import httpx
from github import Github, Auth
from triage.config import settings
from triage.models import TriageReport
from triage.formatters.markdown import format_markdown_pr_comment, COMMENT_MARKER

logger = logging.getLogger("triage.github")


class GitHubTriageClient:
    """Manages interactions with GitHub Actions API and Pull Request comments."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        if self.token:
            auth = Auth.Token(self.token)
            self.gh = Github(auth=auth)
        else:
            self.gh = None

    def post_or_update_pr_comment(self, repo_name: str, pr_number: int, report: TriageReport) -> str:
        """Posts a new PR comment or edits an existing bot comment to avoid spam."""
        if not self.gh:
            raise ValueError("GITHUB_TOKEN is required to comment on PRs")

        repo = self.gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        comment_body = format_markdown_pr_comment(report)

        # Search for existing bot comment with the marker
        existing_comment = None
        for comment in pr.get_issue_comments():
            if COMMENT_MARKER in comment.body:
                existing_comment = comment
                break

        if existing_comment:
            logger.info(f"Updating existing triage comment #{existing_comment.id} on PR #{pr_number}")
            existing_comment.edit(comment_body)
            return f"Updated existing comment #{existing_comment.id}"
        else:
            logger.info(f"Creating new triage comment on PR #{pr_number}")
            new_comment = pr.create_issue_comment(comment_body)
            return f"Created comment #{new_comment.id}"

    async def fetch_workflow_run_logs(self, repo_name: str, run_id: int) -> str:
        """Downloads and extracts all text logs for a given workflow run."""
        if not self.token:
            raise ValueError("GITHUB_TOKEN is required to download workflow logs")

        url = f"https://api.github.com/repos/{repo_name}/actions/runs/{run_id}/logs"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()

            combined_logs = []
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                for filename in z.namelist():
                    if filename.endswith(".txt"):
                        with z.open(filename) as f:
                            text = f.read().decode("utf-8", errors="replace")
                            combined_logs.append(f"=== File: {filename} ===\n{text}")

            return "\n\n".join(combined_logs)
