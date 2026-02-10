"""Gateway management commands"""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ..config.loader import load_config

console = Console()
gateway_app = typer.Typer(help="Gateway server management")


@gateway_app.command("run")
def run(
    port: int = typer.Option(None, "--port", "-p", help="WebSocket port"),
    bind: str = typer.Option("loopback", "--bind", help="Bind mode (loopback|lan|auto)"),
    force: bool = typer.Option(False, "--force", help="Kill existing listener on port"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """Run the Gateway server (foreground)"""
    try:
        import logging
        import subprocess
        import signal
        from ..gateway.bootstrap import GatewayBootstrap
        
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        config = load_config()
        
        if port:
            if not config.gateway:
                from ..config.schema import GatewayConfig
                config.gateway = GatewayConfig()
            config.gateway.port = port
        
        gateway_port = config.gateway.port if config.gateway else 18789
        web_port = 8080  # Control UI port
        
        # If --force, kill any processes on the target ports
        if force:
            for check_port in [gateway_port, web_port]:
                try:
                    result = subprocess.run(
                        ["lsof", "-ti", f":{check_port}"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pids = result.stdout.strip().split("\n")
                        for pid in pids:
                            if pid:
                                console.print(f"[yellow]Killing process {pid} on port {check_port}[/yellow]")
                                try:
                                    subprocess.run(["kill", "-9", pid], check=False)
                                except Exception:
                                    pass
                        import time
                        time.sleep(1)  # Wait for ports to be released
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not check/clear port {check_port}: {e}[/yellow]")
        
        console.print(f"[cyan]Starting Gateway on port {gateway_port}...[/cyan]")
        
        # Use bootstrap to initialize all components
        bootstrap = GatewayBootstrap()
        
        async def run_with_bootstrap():
            await bootstrap.bootstrap()
            console.print(f"[green]✓[/green] Gateway listening on ws://127.0.0.1:{gateway_port}")
            console.print("Press Ctrl+C to stop\n")
            
            # Keep running forever
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                pass
        
        asyncio.run(run_with_bootstrap())
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Gateway stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@gateway_app.command("status")
def status(
    probe: bool = typer.Option(False, "--probe", help="Probe gateway via RPC"),
    deep: bool = typer.Option(False, "--deep", help="Scan system-level services"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show gateway service status"""
    from ..daemon.service import get_service_manager
    
    try:
        manager = get_service_manager()
        
        if json_output:
            result = {
                "installed": manager.is_installed(),
                "running": manager.is_running() if manager.is_installed() else False,
            }
            console.print(json.dumps(result, indent=2))
            return
        
        table = Table(title="Gateway Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        installed = manager.is_installed()
        table.add_row("Installed", "✓ Yes" if installed else "✗ No")
        
        if installed:
            running = manager.is_running()
            table.add_row("Running", "✓ Yes" if running else "✗ No")
        
        console.print(table)
        
        if probe:
            console.print("\n[yellow]⚠[/yellow]  RPC probe not yet implemented")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@gateway_app.command("install")
def install(
    port: int = typer.Option(None, "--port", help="Gateway port"),
    force: bool = typer.Option(False, "--force", help="Reinstall if already installed"),
):
    """Install the Gateway service (launchd/systemd)"""
    from ..daemon.service import get_service_manager
    
    try:
        manager = get_service_manager()
        
        if manager.is_installed() and not force:
            console.print("[yellow]Gateway service already installed[/yellow]")
            console.print("Use --force to reinstall")
            return
        
        config = load_config()
        if port:
            config.gateway.port = port
        
        console.print("[cyan]Installing Gateway service...[/cyan]")
        manager.install()
        
        console.print("[green]✓[/green] Gateway service installed")
        console.print("\nNext steps:")
        console.print("  openclaw gateway start")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@gateway_app.command("uninstall")
def uninstall():
    """Uninstall the Gateway service"""
    from ..daemon.service import get_service_manager
    
    try:
        manager = get_service_manager()
        
        if not manager.is_installed():
            console.print("[yellow]Gateway service not installed[/yellow]")
            return
        
        console.print("[cyan]Uninstalling Gateway service...[/cyan]")
        manager.uninstall()
        
        console.print("[green]✓[/green] Gateway service uninstalled")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@gateway_app.command("start")
def start():
    """Start the Gateway service"""
    from ..daemon.service import get_service_manager
    
    try:
        manager = get_service_manager()
        
        if not manager.is_installed():
            console.print("[red]Gateway service not installed[/red]")
            console.print("Run: openclaw gateway install")
            raise typer.Exit(1)
        
        if manager.is_running():
            console.print("[yellow]Gateway service already running[/yellow]")
            return
        
        console.print("[cyan]Starting Gateway service...[/cyan]")
        manager.start()
        
        console.print("[green]✓[/green] Gateway service started")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@gateway_app.command("stop")
def stop():
    """Stop the Gateway service"""
    from ..daemon.service import get_service_manager
    
    try:
        manager = get_service_manager()
        
        if not manager.is_installed():
            console.print("[yellow]Gateway service not installed[/yellow]")
            return
        
        if not manager.is_running():
            console.print("[yellow]Gateway service not running[/yellow]")
            return
        
        console.print("[cyan]Stopping Gateway service...[/cyan]")
        manager.stop()
        
        console.print("[green]✓[/green] Gateway service stopped")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@gateway_app.command("restart")
def restart():
    """Restart the Gateway service"""
    from ..daemon.service import get_service_manager
    
    try:
        manager = get_service_manager()
        
        if not manager.is_installed():
            console.print("[red]Gateway service not installed[/red]")
            raise typer.Exit(1)
        
        console.print("[cyan]Restarting Gateway service...[/cyan]")
        manager.restart()
        
        console.print("[green]✓[/green] Gateway service restarted")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@gateway_app.command("call")
def call(
    method: str = typer.Argument(..., help="RPC method name"),
    params: str = typer.Option("{}", "--params", help="JSON params"),
):
    """Call a Gateway RPC method"""
    console.print("[yellow]⚠[/yellow]  Gateway RPC call not yet implemented")
    console.print(f"Method: {method}")
    console.print(f"Params: {params}")


@gateway_app.command("cost")
def cost(
    days: int = typer.Option(30, "--days", help="Number of days"),
):
    """Show cost/usage summary"""
    console.print("[yellow]⚠[/yellow]  Cost tracking not yet implemented")
    console.print(f"Would show last {days} days of usage")
