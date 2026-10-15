"""Command-Line Interface (CLI) for CI/CD Failure Triage Assistant."""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from triage.config import settings
from triage.engine import TriageEngine
from triage.formatters.console import print_rich_report
from triage.formatters.markdown import format_markdown_pr_comment
from triage.integrations.github_client import GitHubTriageClient
from triage.llm.client import get_llm_client

app = typer.Typer(help="🤖 AI-Powered CI/CD Build Failure Triage Assistant CLI")
console = Console()


@app.command(name="analyze")
def analyze(
    log_file: Optional[Path] = typer.Option(None, "--log-file", "-f", help="Path to raw CI log file (reads stdin if not provided)"),
    step_name: str = typer.Option("CI Workflow Step", "--step", "-s", help="Name of the failing step"),
    provider: str = typer.Option("mock", "--provider", "-p", help="LLM Provider ('mock', 'openai', 'ollama')"),
    output_md: Optional[Path] = typer.Option(None, "--output-md", "-o", help="Write Markdown report to file"),
    output_json: Optional[Path] = typer.Option(None, "--output-json", "-j", help="Write JSON report to file"),
    post_pr: Optional[int] = typer.Option(None, "--pr-number", help="Post PR comment to this PR number"),
    repo: Optional[str] = typer.Option(None, "--repo", help="GitHub repo in 'owner/repo' format (required with --pr-number)")
):
    """Analyzes a build failure log, detects root cause, and prints an actionable report."""
    raw_log = ""
    if log_file:
        if not log_file.exists():
            console.print(f"[bold red]Error:[/bold red] Log file '{log_file}' not found.")
            raise typer.Exit(code=1)
        raw_log = log_file.read_text(encoding="utf-8", errors="replace")
    else:
        if not sys.stdin.isatty():
            raw_log = sys.stdin.read()
        else:
            console.print("[bold red]Error:[/bold red] Please provide a log file via --log-file or pipe through stdin.")
            raise typer.Exit(code=1)

    # Initialize Engine with selected LLM client
    llm_client = get_llm_client(provider)
    engine = TriageEngine(llm_client=llm_client)

    with console.status("[bold green]Analyzing build failure logs...[/bold green]", spinner="dots"):
        report = asyncio.run(engine.triage_log(raw_log=raw_log, failed_step_hint=step_name))

    # Print terminal rich report
    print_rich_report(report)

    # Export to Markdown if requested
    if output_md:
        md_text = format_markdown_pr_comment(report)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[green]✔ Saved Markdown report to:[/green] {output_md}")

    # Export to JSON if requested
    if output_json:
        output_json.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[green]✔ Saved JSON report to:[/green] {output_json}")

    # Post to GitHub PR if requested
    if post_pr and repo:
        try:
            gh_client = GitHubTriageClient()
            result_msg = gh_client.post_or_update_pr_comment(repo_name=repo, pr_number=post_pr, report=report)
            console.print(f"[green]✔ GitHub PR Action:[/green] {result_msg}")
        except Exception as e:
            console.print(f"[bold red]Failed to post to GitHub PR:[/bold red] {e}")


@app.command(name="serve")
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host address to bind"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to listen on")
):
    """Starts the FastAPI GitHub Webhook Server."""
    import uvicorn
    console.print(f"[bold cyan]Starting AI Triage Webhook Server on {host}:{port}...[/bold cyan]")
    uvicorn.run("triage.integrations.webhook_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
