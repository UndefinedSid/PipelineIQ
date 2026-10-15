"""Unit tests for Markdown and Slack formatters."""

from triage.models import TriageReport, ErrorCategory, ErrorContext, CodeFix
from triage.formatters.markdown import format_markdown_pr_comment, COMMENT_MARKER
from triage.formatters.slack import format_slack_block_kit


def test_format_markdown_pr_comment():
    report = TriageReport(
        id="trg-12345678",
        error_category=ErrorCategory.OUT_OF_MEMORY_OOM,
        confidence_score=0.98,
        summary="Container killed by OOM killer.",
        failed_step="Build Image",
        root_cause_file="Dockerfile",
        root_cause_line=12,
        suggested_fix="Increase RAM allocation.",
        code_fix=CodeFix(unified_diff="- RUN pip install torch\n+ RUN pip install --no-cache-dir torch\n"),
        reproduction_command="docker build -m 4g .",
        triage_mode="AI_LLM",
        context=ErrorContext(raw_error_snippet="exit code 137", total_log_lines=50, extracted_lines=10)
    )

    md = format_markdown_pr_comment(report)
    assert COMMENT_MARKER in md
    assert "CRITICAL - OOM" in md
    assert "Dockerfile:12" in md
    assert "Suggested Code Fix" in md
    assert "docker build -m 4g ." in md


def test_format_slack_block_kit():
    report = TriageReport(
        id="trg-12345678",
        error_category=ErrorCategory.DEPENDENCY_CONFLICT,
        confidence_score=0.94,
        summary="Missing package dependency.",
        failed_step="Install Dependencies",
        suggested_fix="Run npm install.",
        triage_mode="HEURISTIC",
        context=ErrorContext(raw_error_snippet="npm ERR! code ERESOLVE")
    )

    slack_json = format_slack_block_kit(report, repo_name="my-org/web-app", pr_url="https://github.com/my-org/web-app/pull/42")
    assert "blocks" in slack_json
    assert len(slack_json["blocks"]) >= 3
    assert "my-org/web-app" in str(slack_json)
