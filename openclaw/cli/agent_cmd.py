"""Agent execution and management commands"""

import json

import typer
from rich.console import Console
from rich.table import Table

from ..config.loader import load_config

console = Console()
agent_app = typer.Typer(help="Agent execution and management", no_args_is_help=True)

# Create agents subcommand group
agents_app = typer.Typer(help="Manage isolated agents")
agent_app.add_typer(agents_app, name="agents")


@agent_app.command("run")
def run(
    message: str = typer.Option(..., "--message", "-m", help="Message for the agent"),
    to: str = typer.Option(None, "--to", "-t", help="Recipient number"),
    session_id: str = typer.Option(None, "--session-id", help="Explicit session id"),
    agent_id: str = typer.Option(None, "--agent", help="Agent id"),
    thinking: str = typer.Option(None, "--thinking", help="Thinking level (off|low|medium|high)"),
    channel: str = typer.Option(None, "--channel", help="Delivery channel"),
    deliver: bool = typer.Option(False, "--deliver", help="Send reply back to channel"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    timeout: int = typer.Option(600, "--timeout", help="Timeout in seconds"),
):
    """Run an agent turn via the Gateway"""
    import asyncio
    import uuid
    from ..gateway.rpc_client import GatewayRPCClient
    
    try:
        # Generate session ID if not provided
        if not session_id:
            session_id = f"cli-{uuid.uuid4().hex[:8]}"
        
        # Create RPC client
        config = load_config()
        client = GatewayRPCClient(config=config)
        
        # Prepare parameters
        params = {
            "message": message,
            "sessionId": session_id,
        }
        
        if agent_id:
            params["agentId"] = agent_id
        if thinking:
            params["thinking"] = thinking
        if channel:
            params["channel"] = channel
        if to:
            params["to"] = to
        
        # Execute agent turn
        console.print(f"[cyan]→[/cyan] Running agent (session: {session_id})...")
        
        result = asyncio.run(client.call_agent_turn(
            message=message,
            session_id=session_id,
            agent_id=agent_id,
            thinking=thinking,
            timeout=timeout,
        ))
        
        if json_output:
            console.print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        
        # Display response
        if result.get("error"):
            console.print(f"[red]Error:[/red] {result['error']}")
            raise typer.Exit(1)
        
        response = result.get("response", {})
        
        # Display assistant message
        if "text" in response:
            console.print("\n[green]Assistant:[/green]")
            console.print(response["text"])
        
        # Display tool calls if any
        if "toolCalls" in response and response["toolCalls"]:
            console.print("\n[yellow]Tool Calls:[/yellow]")
            for tool_call in response["toolCalls"]:
                console.print(f"  • {tool_call.get('name', 'unknown')}")
        
        # Display usage if available
        if "usage" in result:
            usage = result["usage"]
            console.print(f"\n[dim]Tokens: {usage.get('totalTokens', 0)} | Cost: ${usage.get('cost', 0):.4f}[/dim]")
        
    except ConnectionError as e:
        console.print(f"[red]Connection Error:[/red] Gateway not running on configured port")
        console.print(f"Please start the gateway: [cyan]openclaw gateway run[/cyan]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if "--verbose" in typer.get_app_dir("openclaw"):
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@agents_app.command("list")
def list_agents(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    bindings: bool = typer.Option(False, "--bindings", help="Include routing bindings"),
):
    """List configured agents"""
    try:
        config = load_config()
        
        if not config.agents or not config.agents.agents:
            console.print("[yellow]No agents configured[/yellow]")
            return
        
        if json_output:
            agents_data = [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "workspace": agent.workspace,
                }
                for agent in config.agents.agents
            ]
            console.print(json.dumps(agents_data, indent=2))
            return
        
        table = Table(title="Configured Agents")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Workspace", style="yellow")
        
        for agent in config.agents.agents:
            table.add_row(
                agent.id,
                agent.name or "-",
                agent.workspace or "-",
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@agents_app.command("add")
def add(
    name: str = typer.Argument(None, help="Agent name"),
    workspace: str = typer.Option(None, "--workspace", help="Workspace directory"),
    model: str = typer.Option(None, "--model", help="Model id"),
    agent_dir: str = typer.Option(None, "--agent-dir", help="Agent state directory"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Add a new isolated agent"""
    console.print("[yellow]⚠[/yellow]  Agent creation not yet implemented")
    console.print(f"\nWould create agent: {name or '(default)'}")


@agents_app.command("delete")
def delete(
    id: str = typer.Argument(..., help="Agent id to delete"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Delete an agent and prune workspace/state"""
    console.print("[yellow]⚠[/yellow]  Agent deletion not yet implemented")
    console.print(f"\nWould delete agent: {id}")


@agents_app.command("set-identity")
def set_identity(
    agent_id: str = typer.Option(None, "--agent", help="Agent id to update"),
    workspace: str = typer.Option(None, "--workspace", help="Workspace directory"),
    name: str = typer.Option(None, "--name", help="Identity name"),
    theme: str = typer.Option(None, "--theme", help="Identity theme"),
    emoji: str = typer.Option(None, "--emoji", help="Identity emoji"),
    avatar: str = typer.Option(None, "--avatar", help="Identity avatar"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Update an agent identity"""
    console.print("[yellow]⚠[/yellow]  Agent identity update not yet implemented")
    if agent_id:
        console.print(f"\nWould update agent: {agent_id}")
