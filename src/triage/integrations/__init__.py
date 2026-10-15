"""External integrations subsystem (GitHub API, Slack Webhooks, FastAPI Webhook Server)."""

from triage.integrations.github_client import GitHubTriageClient
from triage.integrations.slack_client import post_to_slack
from triage.integrations.webhook_server import app as webhook_app

__all__ = ["GitHubTriageClient", "post_to_slack", "webhook_app"]
