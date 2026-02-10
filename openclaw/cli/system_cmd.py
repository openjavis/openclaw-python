"""System and event commands"""

import typer
from rich.console import Console

console = Console()
system_app = typer.Typer(help="System events and heartbeats")


@system_app.command("events")
def events(
    follow: bool = typer.Option(False, "--follow", help="Follow events"),
    filter_event: str = typer.Option(None, "--filter", help="Event type filter"),
):
    """List/follow gateway system events"""
    console.print("[yellow]⚠[/yellow]  System events not yet implemented")


@system_app.command("heartbeat")
def heartbeat(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """Ping gateway heartbeat"""
    console.print("[yellow]⚠[/yellow]  Heartbeat not yet implemented")


@system_app.command("presence")
def presence(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """Show presence state"""
    console.print("[yellow]⚠[/yellow]  Presence not yet implemented")
