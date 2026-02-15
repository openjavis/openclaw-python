"""Pairing management commands"""

import typer
from rich.console import Console
from rich.table import Table

console = Console()
pairing_app = typer.Typer(help="Channel pairing management")


@pairing_app.command("list")
def list_pairing_requests(
    channel: str = typer.Argument(..., help="Channel name (telegram, discord, etc)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """List pending pairing requests"""
    try:
        from ..pairing.pairing_store import get_storage
        
        storage = get_storage()
        data = storage.load_pairing_requests(channel)
        requests = data.get("requests", [])
        
        if not requests:
            console.print(f"[yellow]No pending pairing requests for {channel}[/yellow]")
            return
        
        if json_output:
            import json
            console.print(json.dumps(requests, indent=2))
            return
        
        table = Table(title=f"Pending Pairing Requests - {channel}")
        table.add_column("Code", style="cyan", no_wrap=True)
        table.add_column("Sender ID", style="green")
        table.add_column("Username", style="yellow")
        table.add_column("Name", style="white")
        table.add_column("Created", style="blue")
        
        for req in requests:
            meta = req.get("meta", {})
            username = meta.get("username", "-")
            full_name = meta.get("full_name", "-")
            
            table.add_row(
                req["code"],
                req["id"],
                f"@{username}" if username and username != "-" else "-",
                full_name,
                req["created_at"][:10]  # Just date
            )
        
        console.print(table)
        console.print(f"\n[dim]Approve with: uv run openclaw pairing approve {channel} <code>[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@pairing_app.command("approve")
def approve_pairing_request(
    channel: str = typer.Argument(..., help="Channel name (telegram, discord, etc)"),
    code: str = typer.Argument(..., help="Pairing code to approve"),
):
    """Approve a pairing request"""
    try:
        from ..pairing.pairing_store import approve_channel_pairing_code
        
        console.print(f"[cyan]Approving pairing request...[/cyan]")
        console.print(f"  Channel: {channel}")
        console.print(f"  Code: {code}")
        
        result = approve_channel_pairing_code(channel, code)
        
        if result:
            sender_id = result["id"]
            entry_data = result["entry"]
            
            console.print(f"\n[green]✓[/green] Pairing request approved!")
            console.print(f"  Sender ID: {sender_id}")
            
            # Show metadata if available
            if hasattr(entry_data, "meta") and entry_data.meta:
                console.print(f"  Username: {entry_data.meta.get('username', 'N/A')}")
                console.print(f"  Name: {entry_data.meta.get('full_name', 'N/A')}")
            
            console.print(f"\n[dim]Sender has been added to the allowFrom list.[/dim]")
            console.print(f"[dim]They can now send direct messages.[/dim]")
            
            # Suggest notifying the user
            if channel == "telegram":
                console.print(f"\n💡 [dim]You may want to notify them on Telegram that they've been approved.[/dim]")
        else:
            console.print(f"[red]✗[/red] Pairing code not found or expired")
            console.print(f"\n[yellow]Use 'uv run openclaw pairing list {channel}' to see pending requests[/yellow]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@pairing_app.command("deny")
def deny_pairing_request(
    channel: str = typer.Argument(..., help="Channel name"),
    code: str = typer.Argument(..., help="Pairing code to deny"),
):
    """Deny a pairing request"""
    try:
        from ..pairing.pairing_store import get_storage
        
        storage = get_storage()
        data = storage.load_pairing_requests(channel)
        requests = data.get("requests", [])
        
        # Find and remove the request
        found = False
        remaining = []
        for req in requests:
            if req["code"] == code:
                found = True
                console.print(f"[yellow]Denied pairing request:[/yellow]")
                console.print(f"  Code: {code}")
                console.print(f"  Sender: {req['id']}")
            else:
                remaining.append(req)
        
        if found:
            data["requests"] = remaining
            storage.save_pairing_requests(channel, data)
            console.print(f"\n[green]✓[/green] Request removed")
        else:
            console.print(f"[red]✗[/red] Pairing code not found")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@pairing_app.command("clear")
def clear_pairing_requests(
    channel: str = typer.Argument(..., help="Channel name"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all pending pairing requests"""
    try:
        from ..pairing.pairing_store import get_storage
        
        storage = get_storage()
        data = storage.load_pairing_requests(channel)
        requests = data.get("requests", [])
        
        if not requests:
            console.print(f"[yellow]No pending requests for {channel}[/yellow]")
            return
        
        if not confirm:
            response = input(f"\n⚠️  Clear {len(requests)} pending request(s)? [y/N]: ").strip().lower()
            if response != "y":
                console.print("Cancelled")
                return
        
        # Clear all requests
        data["requests"] = []
        storage.save_pairing_requests(channel, data)
        
        console.print(f"[green]✓[/green] Cleared {len(requests)} pairing request(s)")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@pairing_app.command("allowlist")
def show_allowlist(
    channel: str = typer.Argument(..., help="Channel name"),
):
    """Show allowFrom list for a channel"""
    try:
        from ..pairing.pairing_store import read_channel_allow_from_store
        from ..config.loader import load_config
        
        # Get config entries
        config = load_config()
        config_entries = []
        
        if channel == "telegram" and config.channels and config.channels.telegram:
            config_entries = config.channels.telegram.allowFrom or []
        
        # Get combined list
        all_entries = read_channel_allow_from_store(channel, config_entries)
        
        if not all_entries:
            console.print(f"[yellow]No entries in allowFrom list for {channel}[/yellow]")
            console.print(f"\n💡 [dim]Users with pairing mode will need approval[/dim]")
            return
        
        table = Table(title=f"AllowFrom List - {channel}")
        table.add_column("Entry", style="cyan")
        table.add_column("Source", style="yellow")
        
        for entry in all_entries:
            source = "config" if entry in config_entries else "pairing"
            table.add_row(entry, source)
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(all_entries)} allowed sender(s)[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
