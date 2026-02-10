"""Sandbox management commands"""

import typer
from rich.console import Console

console = Console()
sandbox_app = typer.Typer(help="Sandbox tools")


@sandbox_app.command("status")
def status(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """Show sandbox status"""
    console.print("[yellow]⚠[/yellow]  Sandbox status not yet implemented")


@sandbox_app.command("test")
def test():
    """Test sandbox capabilities"""
    console.print("[yellow]⚠[/yellow]  Sandbox testing not yet implemented")
