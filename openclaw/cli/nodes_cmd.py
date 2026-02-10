"""Nodes/devices management commands"""

import typer
from rich.console import Console

console = Console()
nodes_app = typer.Typer(help="Node and device management")


@nodes_app.command("list")
def list_nodes(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """List paired nodes/devices"""
    console.print("[yellow]⚠[/yellow]  Nodes listing not yet implemented")


@nodes_app.command("pair")
def pair(
    code: str = typer.Option(None, "--code", help="Pairing code"),
    name: str = typer.Option(None, "--name", help="Device name"),
):
    """Pair a new device"""
    console.print("[yellow]⚠[/yellow]  Device pairing not yet implemented")


@nodes_app.command("unpair")
def unpair(device_id: str = typer.Argument(..., help="Device id")):
    """Unpair a device"""
    console.print("[yellow]⚠[/yellow]  Device unpairing not yet implemented")
    console.print(f"Would unpair device: {device_id}")


# Default action
@nodes_app.callback(invoke_without_command=True)
def nodes_default(ctx: typer.Context):
    """List nodes (default command)"""
    if ctx.invoked_subcommand is None:
        list_nodes()
