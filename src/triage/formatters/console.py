"""Rich terminal console formatter."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from triage.models import TriageReport
from triage.classifier.taxonomy import CATEGORY_METADATA

console = Console()


def print_rich_report(report: TriageReport):
    """Renders a beautiful colorized terminal summary."""
    meta = CATEGORY_METADATA.get(report.error_category, {})
    badge = meta.get("badge", report.error_category.value)
    confidence_pct = int(report.confidence_score * 100)

    # Main Details Table
    table = Table(title="🤖 CI/CD Failure Triage Report", show_header=False, expand=True)
    table.add_column("Property", style="bold cyan", width=22)
    table.add_column("Value", style="white")

    table.add_row("Error Category", f"[bold red]{badge}[/bold red]")
    table.add_row("Confidence Score", f"{confidence_pct}%")
    table.add_row("Triage Mode", f"[green]{report.triage_mode}[/green]")
    table.add_row("Failed Step", f"[yellow]{report.failed_step}[/yellow]")

    loc = f"{report.root_cause_file}:{report.root_cause_line}" if report.root_cause_file else "N/A"
    table.add_row("Root Cause Location", loc)
    table.add_row("Executive Summary", report.summary)
    table.add_row("Suggested Fix", report.suggested_fix)

    if report.reproduction_command:
        table.add_row("Repro Command", f"[bold green]{report.reproduction_command}[/bold green]")

    console.print(Panel(table, border_style="bright_blue"))

    # Code Diff Panel
    if report.code_fix and report.code_fix.unified_diff:
        syntax = Syntax(report.code_fix.unified_diff, "diff", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title="🛠️ Proposed Code Diff Fix", border_style="green"))

    # Extracted Stacktrace Snippet
    snippet = report.context.extracted_stacktrace or report.context.raw_error_snippet
    if snippet:
        snippet_sample = "\n".join(snippet.splitlines()[:15])
        console.print(Panel(snippet_sample, title=f"🔍 Extracted Stack Trace Sample ({report.context.extracted_lines} lines)", border_style="dim"))
