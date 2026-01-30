#!/usr/bin/env python3
"""
Enhanced CLI for ClawdBot
"""

import asyncio
import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .agents.runtime import AgentRuntime
from .agents.session import SessionManager
from .channels.registry import ChannelRegistry
from .config.settings import Settings, get_settings
from .monitoring import get_health_check, get_metrics, setup_logging

app = typer.Typer(
    name="openclaw",
    help="ClawdBot - Personal AI Assistant Platform",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


# Config commands
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(format: str = typer.Option("table", help="Output format (table/json)")):
    """Show current configuration"""
    settings = get_settings()

    if format == "json":
        console.print_json(json.dumps(settings.to_dict(), default=str))
        return

    # Table format
    table = Table(title="ClawdBot Configuration", box=box.ROUNDED)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    def add_section(section_name: str, config_dict: dict):
        """Add a configuration section to table"""
        table.add_row(f"[bold]{section_name}[/bold]", "", end_section=True)
        for key, value in config_dict.items():
            if isinstance(value, dict):
                continue  # Skip nested dicts in table view
            table.add_row(f"  {key}", str(value))

    add_section("Workspace", {"workspace_dir": settings.workspace_dir})
    add_section("Agent", settings.agent.model_dump())
    add_section("Tools", settings.tools.model_dump())
    add_section("API", settings.api.model_dump())
    add_section("Monitoring", settings.monitoring.model_dump())

    console.print(table)


@config_app.command("save")
def config_save(path: Path = typer.Argument(..., help="Path to save configuration")):
    """Save configuration to file"""
    settings = get_settings()
    settings.save_to_file(path)
    console.print(f"✅ Configuration saved to [cyan]{path}[/cyan]")


@config_app.command("load")
def config_load(path: Path = typer.Argument(..., help="Path to load configuration from")):
    """Load configuration from file"""
    try:
        Settings.load_from_file(path)
        console.print(f"✅ Configuration loaded from [cyan]{path}[/cyan]")
        console.print("\n⚠️  Restart required for changes to take effect")
    except Exception as e:
        console.print(f"❌ Error loading configuration: {e}", style="red")
        raise typer.Exit(1)


# Agent commands
agent_app = typer.Typer(help="Agent operations")
app.add_typer(agent_app, name="agent")


@agent_app.command("chat")
def agent_chat(
    message: str = typer.Argument(..., help="Message to send to agent"),
    session_id: str = typer.Option("cli-session", help="Session ID"),
    model: str | None = typer.Option(None, help="Model to use"),
    workspace: Path | None = typer.Option(None, help="Workspace directory"),
):
    """
    Chat with agent (one-shot)

    Example: openclaw agent chat "Hello, who are you?"
    """

    async def run():
        settings = get_settings()
        ws = workspace or settings.workspace_dir

        # Setup logging
        setup_logging(
            level=settings.monitoring.log_level, format_type=settings.monitoring.log_format
        )

        # Create runtime
        runtime = AgentRuntime(
            model=model or settings.agent.model,
            enable_context_management=settings.agent.enable_context_management,
        )

        # Create session
        session_manager = SessionManager(ws)
        session = session_manager.get_session(session_id)

        # Send message
        console.print("\n[bold cyan]Agent:[/bold cyan]")

        full_response = ""
        async for event in runtime.run_turn(session, message):
            if event.type == "assistant":
                delta = event.data.get("delta", {})
                if "text" in delta:
                    text = delta["text"]
                    console.print(text, end="")
                    full_response += text
            elif event.type == "tool":
                tool_name = event.data.get("toolName")
                console.print(f"\n[dim]  [Tool: {tool_name}][/dim]")

        console.print(f"\n\n[dim]Session: {session_id} | Messages: {len(session.messages)}[/dim]")

    asyncio.run(run())


@agent_app.command("sessions")
def agent_sessions(workspace: Path | None = typer.Option(None, help="Workspace directory")):
    """List all agent sessions"""
    settings = get_settings()
    ws = workspace or settings.workspace_dir

    session_manager = SessionManager(ws)
    sessions = session_manager.list_sessions()

    if not sessions:
        console.print("📭 No sessions found")
        return

    table = Table(title=f"Agent Sessions ({len(sessions)})", box=box.ROUNDED)
    table.add_column("Session ID", style="cyan")
    table.add_column("Messages", style="green")
    table.add_column("Last Modified", style="yellow")

    for session_id in sessions:
        session = session_manager.get_session(session_id)
        session_file = ws / ".sessions" / f"{session_id}.json"

        if session_file.exists():
            mtime = session_file.stat().st_mtime
            from datetime import datetime

            last_modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        else:
            last_modified = "Unknown"

        table.add_row(session_id, str(len(session.messages)), last_modified)

    console.print(table)


# Health commands
health_app = typer.Typer(help="Health check and monitoring")
app.add_typer(health_app, name="health")


@health_app.command("check")
def health_check():
    """Run health checks"""

    async def run():
        health = get_health_check()

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("Running health checks...", total=None)
            result = await health.check_all()
            progress.remove_task(task)

        # Show results
        status_color = {"healthy": "green", "degraded": "yellow", "unhealthy": "red"}.get(
            result.status, "white"
        )

        console.print(
            Panel(
                f"[bold {status_color}]{result.status.upper()}[/bold {status_color}]",
                title="Overall Health",
                box=box.DOUBLE,
            )
        )

        if result.components:
            table = Table(title="Components", box=box.ROUNDED)
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Message", style="dim")
            table.add_column("Response Time", style="yellow")

            for name, component in result.components.items():
                status = component["status"]
                status_emoji = "✅" if status == "healthy" else "❌"
                response_time = component.get("responseTimeMs")
                response_str = f"{response_time:.1f}ms" if response_time else "N/A"

                table.add_row(
                    name, f"{status_emoji} {status}", component.get("message", ""), response_str
                )

            console.print(table)

        console.print(f"\n[dim]Uptime: {result.uptime_seconds:.1f}s[/dim]")

    asyncio.run(run())


@health_app.command("metrics")
def health_metrics(
    format: str = typer.Option("table", help="Output format (table/json/prometheus)")
):
    """Show metrics"""
    metrics = get_metrics()

    if format == "json":
        console.print_json(json.dumps(metrics.to_dict(), default=str))
        return

    if format == "prometheus":
        console.print(metrics.to_prometheus())
        return

    # Table format
    data = metrics.to_dict()

    # Counters
    if data["counters"]:
        table = Table(title="Counters", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Value", style="green")

        for counter in data["counters"].values():
            table.add_row(counter["name"], f"{counter['value']:.0f}")

        console.print(table)

    # Gauges
    if data["gauges"]:
        table = Table(title="Gauges", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Value", style="green")

        for gauge in data["gauges"].values():
            table.add_row(gauge["name"], f"{gauge['value']:.2f}")

        console.print(table)

    # Histograms
    if data["histograms"]:
        table = Table(title="Histograms", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Count", style="blue")
        table.add_column("Avg", style="green")
        table.add_column("P95", style="yellow")
        table.add_column("P99", style="red")

        for hist in data["histograms"].values():
            table.add_row(
                hist["name"],
                str(hist["count"]),
                f"{hist['avg']:.3f}",
                f"{hist['p95']:.3f}",
                f"{hist['p99']:.3f}",
            )

        console.print(table)


# API server commands
api_app = typer.Typer(help="API server management")
app.add_typer(api_app, name="api")


@api_app.command("start")
def api_start(
    host: str | None = typer.Option(None, help="Host to bind to"),
    port: int | None = typer.Option(None, help="Port to bind to"),
):
    """Start API server"""

    async def run():
        from .agents.runtime import AgentRuntime
        from .agents.session import SessionManager
        from .api import run_api_server

        settings = get_settings()

        # Setup logging
        setup_logging(
            level=settings.monitoring.log_level, format_type=settings.monitoring.log_format
        )

        # Create components
        runtime = AgentRuntime(
            model=settings.agent.model,
            enable_context_management=settings.agent.enable_context_management,
        )
        session_manager = SessionManager(settings.workspace_dir)
        channel_registry = ChannelRegistry()

        # Run server
        console.print(
            f"\n🚀 Starting API server on {host or settings.api.host}:{port or settings.api.port}"
        )
        console.print(
            f"📚 Docs: http://{host or settings.api.host}:{port or settings.api.port}/docs\n"
        )

        await run_api_server(
            host=host or settings.api.host,
            port=port or settings.api.port,
            runtime=runtime,
            session_manager=session_manager,
            channel_registry=channel_registry,
        )

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n✅ Server stopped")


# Main command
@app.command()
def version():
    """Show version information"""
    console.print(
        Panel(
            "[bold cyan]ClawdBot[/bold cyan] v0.3.2\n"
            "Personal AI Assistant Platform\n\n"
            "[dim]Python Implementation[/dim]",
            box=box.DOUBLE,
        )
    )


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version_flag: bool = typer.Option(False, "--version", "-v", help="Show version"),
):
    """ClawdBot - Personal AI Assistant Platform"""
    if version_flag:
        version()
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print("[bold cyan]ClawdBot CLI[/bold cyan]\n")
        console.print("Available commands:")
        console.print("  [cyan]agent[/cyan]   - Agent operations")
        console.print("  [cyan]config[/cyan]  - Configuration management")
        console.print("  [cyan]health[/cyan]  - Health check and monitoring")
        console.print("  [cyan]api[/cyan]     - API server management")
        console.print("\nUse [cyan]--help[/cyan] for more information on any command")


if __name__ == "__main__":
    app()
