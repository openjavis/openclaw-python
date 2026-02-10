"""Tools CLI commands"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

tools_app = typer.Typer(help="Manage agent tools")
console = Console()


@tools_app.command("list")
def list_tools(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show more details"),
):
    """List all available agent tools"""
    try:
        # Define tool metadata (name and description) for all tools
        # This matches the tools registered in gateway bootstrap
        tools_metadata = [
            {"name": "bash", "description": "Execute bash commands"},
            {"name": "read_file", "description": "Read file contents"},
            {"name": "write_file", "description": "Write file contents"},
            {"name": "edit_file", "description": "Edit file with search/replace"},
            {"name": "apply_patch", "description": "Apply unified diff patch to files"},
            {"name": "web_search", "description": "Search the web using DuckDuckGo"},
            {"name": "web_fetch", "description": "Fetch web page contents"},
            {"name": "image", "description": "Analyze images using vision models"},
            {"name": "browser", "description": "Control browser for web automation"},
            {"name": "canvas", "description": "Control visual workspace for UI display"},
            {"name": "cron", "description": "Manage scheduled tasks and reminders"},
            {"name": "tts", "description": "Convert text to speech"},
            {"name": "process", "description": "Manage system processes"},
            {"name": "message", "description": "Send messages to channels"},
            {"name": "nodes", "description": "Control connected devices (camera, screen, location)"},
            {"name": "sessions_list", "description": "List all active sessions"},
            {"name": "sessions_history", "description": "Get session history"},
            {"name": "sessions_send", "description": "Send message to another session"},
            {"name": "sessions_spawn", "description": "Create a new session"},
            {"name": "gateway", "description": "Interact with OpenClaw gateway"},
            {"name": "agents_list", "description": "List configured agents"},
            {"name": "session_status", "description": "Get current session status"},
            {"name": "voice_call", "description": "Make and receive voice calls"},
        ]
        
        all_tools = tools_metadata
        
        if json_output:
            console.print(json.dumps(all_tools, indent=2))
            return
        
        if not all_tools:
            console.print("[yellow]No tools found[/yellow]")
            return
        
        table = Table(title=f"Agent Tools ({len(all_tools)})")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        
        for tool in all_tools:
            desc = tool.get("description", "")
            if not verbose and len(desc) > 80:
                desc = desc[:80] + "..."
            table.add_row(tool["name"], desc)
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback
        if verbose:
            console.print(traceback.format_exc())
        raise typer.Exit(1)


@tools_app.command("info")
def info(
    name: str = typer.Argument(..., help="Tool name"),
):
    """Show detailed information about a specific tool"""
    try:
        # Use the same metadata as list command
        tools_metadata = [
            {"name": "bash", "description": "Execute bash commands in a shell", "params": ["command"]},
            {"name": "read_file", "description": "Read file contents from the filesystem", "params": ["path"]},
            {"name": "write_file", "description": "Write file contents to the filesystem", "params": ["path", "contents"]},
            {"name": "edit_file", "description": "Edit file with search/replace operations", "params": ["path", "old_string", "new_string"]},
            {"name": "apply_patch", "description": "Apply unified diff patch to files", "params": ["path", "patch"]},
            {"name": "web_search", "description": "Search the web using DuckDuckGo", "params": ["query"]},
            {"name": "web_fetch", "description": "Fetch web page contents from a URL", "params": ["url"]},
            {"name": "image", "description": "Analyze images using vision models", "params": ["image_path", "prompt"]},
            {"name": "browser", "description": "Control browser for web automation", "params": ["action", "url"]},
            {"name": "canvas", "description": "Control visual workspace for UI display", "params": ["action"]},
            {"name": "cron", "description": "Manage scheduled tasks and reminders", "params": ["action", "task"]},
            {"name": "tts", "description": "Convert text to speech", "params": ["text"]},
            {"name": "process", "description": "Manage system processes", "params": ["action", "process"]},
            {"name": "message", "description": "Send messages to channels", "params": ["channel", "message"]},
            {"name": "nodes", "description": "Control connected devices (camera, screen, location)", "params": ["action", "node"]},
            {"name": "sessions_list", "description": "List all active sessions", "params": []},
            {"name": "sessions_history", "description": "Get session history", "params": ["session_id"]},
            {"name": "sessions_send", "description": "Send message to another session", "params": ["session_id", "message"]},
            {"name": "sessions_spawn", "description": "Create a new session", "params": ["agent_id"]},
            {"name": "gateway", "description": "Interact with OpenClaw gateway", "params": ["action"]},
            {"name": "agents_list", "description": "List configured agents", "params": []},
            {"name": "session_status", "description": "Get current session status", "params": []},
            {"name": "voice_call", "description": "Make and receive voice calls", "params": ["action", "number"]},
        ]
        
        # Find the tool
        tool_info = None
        for tool in tools_metadata:
            if tool["name"] == name:
                tool_info = tool
                break
        
        if not tool_info:
            console.print(f"[red]Error:[/red] Tool '{name}' not found")
            console.print("\nAvailable tools:")
            for t in tools_metadata:
                console.print(f"  • {t['name']}")
            raise typer.Exit(1)
        
        # Display tool information
        console.print(f"\n[bold cyan]{tool_info['name']}[/bold cyan]")
        console.print(f"\n{tool_info['description']}")
        
        # Show parameters
        params = tool_info.get("params", [])
        if params:
            console.print("\n[bold]Parameters:[/bold]")
            for param in params:
                console.print(f"  • {param}")
        else:
            console.print("\n[dim]No parameters required[/dim]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
