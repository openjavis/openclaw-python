"""Status, health, and sessions commands"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..config.loader import load_config

console = Console()
status_app = typer.Typer(help="Status and health checks", no_args_is_help=False)


@status_app.command("status")
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    all_info: bool = typer.Option(False, "--all", help="Full diagnosis"),
    deep: bool = typer.Option(False, "--deep", help="Probe channels"),
    usage: bool = typer.Option(False, "--usage", help="Show usage/quota snapshots"),
    timeout: int = typer.Option(10000, "--timeout", help="Timeout in ms"),
):
    """Show channel health and recent sessions"""
    try:
        config = load_config()
        
        if json_output:
            result = {
                "gateway": {"port": config.gateway.port},
                "agent": {"model": config.agent.model if hasattr(config.agent, 'model') else "default"},
                "channels": {},
            }
            console.print(json.dumps(result, indent=2))
            return
        
        table = Table(title="OpenClaw Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        table.add_row("Gateway", "Configured", f"Port: {config.gateway.port}")
        
        agent_model = config.agent.model if hasattr(config.agent, 'model') else "default"
        table.add_row("Agent", "Configured", f"Model: {agent_model}")
        
        channels_enabled = []
        if config.channels.telegram and config.channels.telegram.enabled:
            channels_enabled.append("telegram")
        if config.channels.whatsapp and config.channels.whatsapp.enabled:
            channels_enabled.append("whatsapp")
        
        channels_str = ", ".join(channels_enabled) if channels_enabled else "None"
        table.add_row("Channels", "Configured", f"Enabled: {channels_str}")
        
        console.print(table)
        
        if deep:
            console.print("\n[yellow]⚠[/yellow]  Deep probe not yet fully implemented")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@status_app.command("health")
def health(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    timeout: int = typer.Option(10000, "--timeout", help="Timeout in ms"),
):
    """Fetch health from the running gateway"""
    console.print("[yellow]⚠[/yellow]  Gateway health check not yet implemented")
    console.print("This would probe the gateway RPC endpoint")


@status_app.command("sessions")
def sessions(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    store: str = typer.Option(None, "--store", help="Session store path"),
    active: int = typer.Option(None, "--active", help="Only show sessions active in last N minutes"),
):
    """List stored conversation sessions"""
    try:
        import json as json_lib
        from datetime import datetime, timedelta
        
        sessions_dir = Path.home() / ".openclaw" / "workspace" / ".sessions"
        
        if not sessions_dir.exists():
            console.print("[yellow]No sessions directory found[/yellow]")
            return
        
        session_files = list(sessions_dir.glob("*.json"))
        
        if json_output:
            sessions_data = []
            for session_file in session_files:
                try:
                    with open(session_file) as f:
                        session_data = json_lib.load(f)
                    sessions_data.append({
                        "id": session_data.get("session_id"),
                        "created": session_data.get("created_at"),
                        "updated": session_data.get("updated_at"),
                        "message_count": len(session_data.get("messages", [])),
                    })
                except:
                    pass
            console.print(json.dumps({"sessions": sessions_data}, indent=2))
            return
        
        if not session_files:
            console.print("[yellow]No sessions found[/yellow]")
            return
        
        table = Table(title=f"Sessions ({len(session_files)})")
        table.add_column("Session ID", style="cyan")
        table.add_column("Messages", style="yellow")
        table.add_column("Last Updated", style="green")
        
        for session_file in session_files:
            try:
                with open(session_file) as f:
                    session_data = json_lib.load(f)
                
                session_id = session_data.get("session_id", session_file.stem)
                message_count = len(session_data.get("messages", []))
                updated_at = session_data.get("updated_at", "")
                
                # Filter by active if specified
                if active:
                    try:
                        updated_time = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        cutoff = datetime.now(updated_time.tzinfo) - timedelta(minutes=active)
                        if updated_time < cutoff:
                            continue
                    except:
                        pass
                
                table.add_row(session_id, str(message_count), updated_at)
            except Exception as e:
                console.print(f"[dim]Skipping {session_file.name}: {e}[/dim]")
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# Register status as default command
@status_app.callback(invoke_without_command=True)
def status_default(ctx: typer.Context):
    """Show status (default command)"""
    if ctx.invoked_subcommand is None:
        status()
