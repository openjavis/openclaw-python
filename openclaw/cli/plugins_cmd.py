"""Plugins management commands"""

import typer
from rich.console import Console

console = Console()
plugins_app = typer.Typer(help="Plugin management")


@plugins_app.command("list")
def list_plugins(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """List installed plugins"""
    console.print("[yellow]⚠[/yellow]  Plugins listing not yet implemented")


@plugins_app.command("install")
def install(plugin: str = typer.Argument(..., help="Plugin name or path")):
    """Install a plugin"""
    console.print("[yellow]⚠[/yellow]  Plugin installation not yet implemented")
    console.print(f"Would install plugin: {plugin}")


@plugins_app.command("remove")
def remove(plugin: str = typer.Argument(..., help="Plugin name")):
    """Remove a plugin"""
    console.print("[yellow]⚠[/yellow]  Plugin removal not yet implemented")
    console.print(f"Would remove plugin: {plugin}")


# Default action
@plugins_app.callback(invoke_without_command=True)
def plugins_default(ctx: typer.Context):
    """List plugins (default command)"""
    if ctx.invoked_subcommand is None:
        list_plugins()
