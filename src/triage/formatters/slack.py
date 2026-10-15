"""Slack Block Kit JSON layout builder."""

from typing import Dict, Any, List
from triage.models import TriageReport
from triage.classifier.taxonomy import CATEGORY_METADATA


def format_slack_block_kit(report: TriageReport, repo_name: str = "repository", pr_url: str = "") -> Dict[str, Any]:
    """Generates Slack Block Kit payload with interactive details and code diffs."""
    meta = CATEGORY_METADATA.get(report.error_category, {})
    emoji = meta.get("emoji", "🚨")
    badge = meta.get("badge", report.error_category.value)

    blocks: List[Dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} CI/CD Build Failure: {report.failed_step}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Category:* `{badge}` (Confidence: {int(report.confidence_score * 100)}%)\n*Summary:* {report.summary}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Repository:*\n`{repo_name}`"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Root Cause File:*\n`{report.root_cause_file or 'N/A'}:{report.root_cause_line or ''}`"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Suggested Action:*\n{report.suggested_fix}"
            }
        }
    ]

    if report.code_fix and report.code_fix.unified_diff:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Proposed Diff:*\n```\n{report.code_fix.unified_diff[:800]}\n```"
            }
        })

    if pr_url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Pull Request",
                        "emoji": True
                    },
                    "url": pr_url,
                    "style": "primary"
                }
            ]
        })

    return {"blocks": blocks}
