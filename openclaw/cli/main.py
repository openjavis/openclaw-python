"""Main CLI application"""

import typer
from rich.console import Console
from rich.table import Table

from ..config import load_config
from .agent_cmd import agent_app
from .channels_cmd import channels_app
from .gateway_cmd import gateway_app

app = typer.Typer(
    name="openclaw", help="ClawdBot - Personal AI Assistant Platform", no_args_is_help=True
)

console = Console()

# Register subcommands
app.add_typer(gateway_app, name="gateway")
app.add_typer(agent_app, name="agent")
app.add_typer(channels_app, name="channels")


@app.command()
def status() -> None:
    """Show ClawdBot status"""
    config = load_config()

    table = Table(title="ClawdBot Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    # Gateway status
    table.add_row(
        "Gateway", "Configured", f"Port: {config.gateway.port}, Bind: {config.gateway.bind}"
    )

    # Agent status
    agent_model = (
        config.agent.model if isinstance(config.agent.model, str) else config.agent.model.primary
    )
    table.add_row("Agent", "Configured", f"Model: {agent_model}")

    # Channels status
    channels_enabled = []
    if config.channels.telegram and config.channels.telegram.enabled:
        channels_enabled.append("telegram")
    if config.channels.whatsapp and config.channels.whatsapp.enabled:
        channels_enabled.append("whatsapp")
    if config.channels.discord and config.channels.discord.enabled:
        channels_enabled.append("discord")

    table.add_row(
        "Channels",
        "Configured",
        f"Enabled: {', '.join(channels_enabled) if channels_enabled else 'None'}",
    )

    console.print(table)


@app.command()
def onboard() -> None:
    """Run onboarding wizard"""
    console.print("[bold cyan]Welcome to ClawdBot![/bold cyan]")
    console.print("\nThis wizard will help you set up your AI assistant.\n")

    # TODO: Implement full onboarding wizard
    config = load_config()

    # Ask for model preference
    console.print("[yellow]Step 1: Choose your AI model[/yellow]")
    console.print("1. Claude Opus 4.5 (Anthropic) - Recommended")
    console.print("2. GPT-4 (OpenAI)")
    console.print("3. Keep default\n")

    choice = typer.prompt("Enter choice", default="3")

    if choice == "1":
        config.agent.model = "anthropic/claude-opus-4-5-20250514"
    elif choice == "2":
        config.agent.model = "openai/gpt-4"

    # Ask for gateway port
    console.print("\n[yellow]Step 2: Gateway configuration[/yellow]")
    port = typer.prompt("Gateway port", default=config.gateway.port)
    config.gateway.port = int(port)

    # Save config
    from ..config.loader import save_config

    save_config(config)

    console.print("\n[green]✓ Configuration saved![/green]")
    console.print("\nNext steps:")
    console.print("1. Start the gateway: [cyan]openclaw gateway start[/cyan]")
    console.print("2. Configure channels: [cyan]openclaw channels login telegram[/cyan]")
    console.print("3. Run agent: [cyan]openclaw agent run 'Hello!'[/cyan]")


@app.command()
def doctor() -> None:
    """Run diagnostics"""
    console.print("[bold cyan]Running ClawdBot diagnostics...[/bold cyan]\n")

    checks = []

    # Check config
    try:
        load_config()
        checks.append(("Configuration", True, "Config loaded successfully"))
    except Exception as e:
        checks.append(("Configuration", False, f"Error: {e}"))

    # Check Python version
    import sys

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append(("Python Version", True, f"Python {py_version}"))

    # Check dependencies
    try:
        import anthropic

        checks.append(("Anthropic SDK", True, "Installed"))
    except ImportError:
        checks.append(("Anthropic SDK", False, "Not installed"))

    try:
        import websockets

        checks.append(("WebSockets", True, "Installed"))
    except ImportError:
        checks.append(("WebSockets", False, "Not installed"))

    # Display results
    table = Table(title="Diagnostic Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")

    for name, passed, details in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        style = "green" if passed else "red"
        table.add_row(name, f"[{style}]{status}[/{style}]", details)

    console.print(table)

    # Summary
    passed_count = sum(1 for _, passed, _ in checks if passed)
    total_count = len(checks)

    if passed_count == total_count:
        console.print(f"\n[green]✓ All checks passed ({passed_count}/{total_count})[/green]")
    else:
        console.print(f"\n[red]✗ {total_count - passed_count} check(s) failed[/red]")


if __name__ == "__main__":
    app()
