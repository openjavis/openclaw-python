"""Cron management commands"""

import typer
from rich.console import Console

console = Console()
cron_app = typer.Typer(help="Scheduled tasks (cron)")


@cron_app.command("list")
def list_crons(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """List cron jobs"""
    try:
        from ..agents.tools.cron import CronTool
        
        cron_tool = CronTool()
        # CronTool uses APScheduler internally
        # For now, show placeholder until we can query the running scheduler
        console.print("[yellow]Cron jobs:[/yellow]")
        console.print("  (Cron tool exists but job listing requires running gateway)")
        console.print("\nTo list jobs, the gateway must be running.")
        console.print("Jobs are managed via the cron tool in agent sessions.")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@cron_app.command("enable")
def enable(name: str = typer.Argument(..., help="Cron job name")):
    """Enable a cron job"""
    console.print("[yellow]⚠[/yellow]  Cron enable not yet implemented")
    console.print(f"Would enable cron: {name}")


@cron_app.command("disable")
def disable(name: str = typer.Argument(..., help="Cron job name")):
    """Disable a cron job"""
    console.print("[yellow]⚠[/yellow]  Cron disable not yet implemented")
    console.print(f"Would disable cron: {name}")


# Default action
@cron_app.callback(invoke_without_command=True)
def cron_default(ctx: typer.Context):
    """List crons (default command)"""
    if ctx.invoked_subcommand is None:
        list_crons()
