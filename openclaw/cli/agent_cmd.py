"""Agent execution commands"""

import typer
from rich.console import Console

console = Console()
agent_app = typer.Typer(help="Run agent commands")


@agent_app.command("run")
def run(
    message: str = typer.Argument(..., help="Message to send to agent"),
    model: str = typer.Option(None, "--model", "-m", help="Model to use"),
    session: str = typer.Option("main", "--session", "-s", help="Session ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run an agent turn with a message"""
    console.print(f"[cyan]Running agent with message:[/cyan] {message}")

    if model:
        console.print(f"[yellow]Using model:[/yellow] {model}")

    # TODO: Implement agent execution
    console.print("[red]Agent execution not implemented yet[/red]")
    console.print("\nThis will:")
    console.print("1. Connect to gateway")
    console.print("2. Send agent request")
    console.print("3. Stream response")


@agent_app.command("list")
def list_agents() -> None:
    """List configured agents"""
    from ..config import load_config

    config = load_config()

    if not config.agents or not config.agents.agents:
        console.print("[yellow]No agents configured[/yellow]")
        return

    console.print("[cyan]Configured Agents:[/cyan]\n")
    for agent in config.agents.agents:
        console.print(f"  • [bold]{agent.id}[/bold]")
        if agent.name:
            console.print(f"    Name: {agent.name}")
        if agent.workspace:
            console.print(f"    Workspace: {agent.workspace}")
        console.print()
