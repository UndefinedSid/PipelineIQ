"""Markdown formatter for GitHub PR comments and Step Summaries."""

from triage.models import TriageReport
from triage.classifier.taxonomy import CATEGORY_METADATA

COMMENT_MARKER = "<!-- AI_CI_TRIAGE_ASSISTANT_BOT_COMMENT -->"


def format_markdown_pr_comment(report: TriageReport) -> str:
    """Formats a full, rich GitHub PR comment with collapsible stack trace and diff."""
    meta = CATEGORY_METADATA.get(report.error_category, {})
    badge = meta.get("badge", f"🔴 {report.error_category.value}")

    confidence_pct = int(report.confidence_score * 100)

    location_str = "N/A"
    if report.root_cause_file:
        if report.root_cause_line:
            location_str = f"`{report.root_cause_file}:{report.root_cause_line}`"
        else:
            location_str = f"`{report.root_cause_file}`"

    diff_block = ""
    if report.code_fix and report.code_fix.unified_diff:
        diff_block = f"""
### 🛠️ Suggested Code Fix
```diff
{report.code_fix.unified_diff.strip()}
```
"""

    repro_block = ""
    if report.reproduction_command:
        repro_block = f"""
### 🧪 Local Reproduction Command
```bash
{report.reproduction_command.strip()}
```
"""

    stacktrace_block = ""
    snippet = report.context.extracted_stacktrace or report.context.raw_error_snippet
    if snippet:
        stacktrace_block = f"""
<details>
<summary>🔍 <b>Extracted Error / Stack Trace ({report.context.extracted_lines} lines analyzed)</b></summary>

```text
{snippet.strip()}
```
</details>
"""

    comment = f"""{COMMENT_MARKER}
## 🤖 CI/CD Build Failure Triage Assistant

> **Status:** {badge} &nbsp;|&nbsp; **Confidence:** `{confidence_pct}%` &nbsp;|&nbsp; **Mode:** `{report.triage_mode}`  
> 📌 **Failed Step:** `{report.failed_step}`  
> 📁 **Location:** {location_str}

### 💡 Executive Root Cause Summary
{report.summary}

### 📋 Recommended Fix
{report.suggested_fix}
{diff_block}{repro_block}{stacktrace_block}
---
*Automated triage generated in `< 2s` • [Report Bug / Docs](https://github.com)*
"""
    return comment.strip()


def format_step_summary(report: TriageReport) -> str:
    """Formats a concise version suitable for $GITHUB_STEP_SUMMARY."""
    return format_markdown_pr_comment(report)
