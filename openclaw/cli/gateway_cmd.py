"""Gateway management commands"""

import asyncio

import typer
from rich.console import Console

console = Console()
gateway_app = typer.Typer(help="Manage the Gateway server")


@gateway_app.command("start")
def start() -> None:
    """Start the Gateway server"""
    console.print("[cyan]Starting Gateway server...[/cyan]")

    try:
        import logging

        from ..config import load_config
        from ..gateway.server import GatewayServer

        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        config = load_config()
        server = GatewayServer(config)

        console.print(f"[green]Gateway listening on ws://127.0.0.1:{config.gateway.port}[/green]")
        console.print("Press Ctrl+C to stop\n")

        asyncio.run(server.start())

    except KeyboardInterrupt:
        console.print("\n[yellow]Gateway stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error starting gateway: {e}[/red]")
        raise typer.Exit(1)


@gateway_app.command("stop")
def stop() -> None:
    """Stop the Gateway server"""
    console.print("[yellow]Stopping Gateway server...[/yellow]")
    # TODO: Implement graceful shutdown via signal or IPC
    console.print("[green]Gateway stopped[/green]")


@gateway_app.command("status")
def status() -> None:
    """Check Gateway server status"""
    console.print("[cyan]Checking Gateway status...[/cyan]")
    # TODO: Implement status check via health endpoint or IPC
    console.print("[yellow]Gateway status: Unknown (not implemented)[/yellow]")


@gateway_app.command("install")
def install() -> None:
    """Install Gateway as a system service"""
    console.print("[yellow]Installing Gateway as system service...[/yellow]")
    # TODO: Implement systemd/launchd service installation
    console.print("[red]Not implemented yet[/red]")
