"""Model configuration commands"""

import json

import typer
from rich.console import Console

console = Console()
models_app = typer.Typer(help="Model discovery, scanning, and configuration")


@models_app.command("list")
def list_models(
    all_models: bool = typer.Option(False, "--all", help="Show full model catalog"),
    local: bool = typer.Option(False, "--local", help="Filter to local models"),
    provider: str = typer.Option(None, "--provider", help="Filter by provider"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    plain: bool = typer.Option(False, "--plain", help="Plain line output"),
):
    """List models (configured by default)"""
    console.print("[yellow]⚠[/yellow]  Model listing not yet implemented")


@models_app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    plain: bool = typer.Option(False, "--plain", help="Plain output"),
    check: bool = typer.Option(False, "--check", help="Exit non-zero if auth expiring/expired"),
    probe: bool = typer.Option(False, "--probe", help="Probe configured provider auth"),
    agent: str = typer.Option(None, "--agent", help="Agent id"),
):
    """Show configured model state"""
    console.print("[yellow]⚠[/yellow]  Model status not yet implemented")


@models_app.command("set")
def set_model(
    model: str = typer.Argument(..., help="Model id or alias"),
):
    """Set the default model"""
    console.print("[yellow]⚠[/yellow]  Model configuration not yet implemented")
    console.print(f"Would set model to: {model}")


@models_app.command("set-image")
def set_image_model(
    model: str = typer.Argument(..., help="Model id or alias"),
):
    """Set the image model"""
    console.print("[yellow]⚠[/yellow]  Image model configuration not yet implemented")
    console.print(f"Would set image model to: {model}")


@models_app.command("scan")
def scan(
    no_probe: bool = typer.Option(False, "--no-probe", help="Skip live probes"),
    yes: bool = typer.Option(False, "--yes", help="Accept defaults without prompting"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Scan OpenRouter free models"""
    console.print("[yellow]⚠[/yellow]  Model scanning not yet implemented")


# Auth subcommands
auth_app = typer.Typer(help="Manage model auth profiles")
models_app.add_typer(auth_app, name="auth")


@auth_app.command("add")
def auth_add():
    """Interactive auth helper"""
    console.print("[yellow]⚠[/yellow]  Auth configuration not yet implemented")


@auth_app.command("login")
def auth_login(
    provider: str = typer.Option(None, "--provider", help="Provider id"),
    method: str = typer.Option(None, "--method", help="Auth method id"),
):
    """Run a provider plugin auth flow"""
    console.print("[yellow]⚠[/yellow]  Provider auth flow not yet implemented")
