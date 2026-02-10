"""Channel management commands"""

import json

import typer
from rich.console import Console
from rich.table import Table

from ..config.loader import load_config

console = Console()
channels_app = typer.Typer(help="Messaging channel management")


@channels_app.command("list")
def list_channels(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """List configured channels"""
    try:
        config = load_config()
        
        if json_output:
            result = {}
            if config.channels.telegram:
                result["telegram"] = {
                    "enabled": config.channels.telegram.enabled,
                    "configured": bool(config.channels.telegram.botToken),
                }
            console.print(json.dumps(result, indent=2))
            return
        
        table = Table(title="Channels")
        table.add_column("Channel", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")
        
        if config.channels.telegram:
            status = "✓ Enabled" if config.channels.telegram.enabled else "✗ Disabled"
            details = "Configured" if config.channels.telegram.botToken else "Not configured"
            table.add_row("Telegram", status, details)
        
        if config.channels.whatsapp:
            status = "✓ Enabled" if config.channels.whatsapp.enabled else "✗ Disabled"
            table.add_row("WhatsApp", status, "")
        
        if config.channels.discord:
            status = "✓ Enabled" if config.channels.discord.enabled else "✗ Disabled"
            table.add_row("Discord", status, "")
        
        if config.channels.slack:
            status = "✓ Enabled" if config.channels.slack.enabled else "✗ Disabled"
            table.add_row("Slack", status, "")
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@channels_app.command("status")
def status(
    probe: bool = typer.Option(False, "--probe", help="Probe channel credentials"),
    timeout: int = typer.Option(10000, "--timeout", help="Timeout in ms"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show channel connection status"""
    console.print("[yellow]⚠[/yellow]  Channel status probe not yet fully implemented")
    list_channels(json_output=json_output)


@channels_app.command("add")
def add(
    channel: str = typer.Argument(..., help="Channel type (telegram, discord, slack)"),
    token: str = typer.Option(None, "--token", help="Bot token"),
    account_id: str = typer.Option(None, "--account-id", help="Account ID"),
    dm_policy: str = typer.Option("pairing", "--dm-policy", help="DM policy (open, pairing, allowlist)"),
):
    """Add or update a channel account"""
    from ..config.loader import save_config
    
    console.print(f"[cyan]Adding {channel} channel...[/cyan]\n")
    
    # Validate channel type
    if channel not in ["telegram", "discord", "slack", "whatsapp"]:
        console.print(f"[red]Unknown channel:[/red] {channel}")
        console.print("Supported channels: telegram, discord, slack, whatsapp")
        raise typer.Exit(1)
    
    # Load config
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        console.print("Run: openclaw onboard")
        raise typer.Exit(1)
    
    # Get token (from option or prompt)
    if token is None:
        import os
        env_var = f"{channel.upper()}_BOT_TOKEN"
        env_token = os.getenv(env_var)
        
        if env_token:
            use_env = typer.confirm(f"Use {env_var} from environment?", default=True)
            if use_env:
                token = env_token
                console.print(f"✓ Using token from {env_var}")
        
        if token is None:
            token = typer.prompt(f"{channel.title()} bot token", hide_input=True)
    
    if not token:
        console.print("[red]Error:[/red] Token is required")
        raise typer.Exit(1)
    
    # Build channel config
    channel_config = {
        "enabled": True,
        "bot_token": token,
        "dm_policy": dm_policy,
    }
    
    if account_id:
        channel_config["account_id"] = account_id
    
    # Update config
    setattr(config.channels, channel, channel_config)
    
    # Save
    try:
        save_config(config)
        console.print(f"\n[green]✓[/green] {channel.title()} channel configured")
        console.print(f"DM Policy: {dm_policy}")
        
        if account_id:
            console.print(f"Account ID: {account_id}")
        
        console.print("\nStart Gateway to activate: openclaw gateway run")
    except Exception as e:
        console.print(f"[red]Error saving config:[/red] {e}")
        raise typer.Exit(1)


@channels_app.command("remove")
def remove(
    channel: str = typer.Argument(..., help="Channel type (telegram, discord, slack)"),
):
    """Remove channel account"""
    from ..config.loader import save_config
    
    console.print(f"[cyan]Removing {channel} channel...[/cyan]\n")
    
    # Validate channel type
    if channel not in ["telegram", "discord", "slack", "whatsapp"]:
        console.print(f"[red]Unknown channel:[/red] {channel}")
        raise typer.Exit(1)
    
    # Load config
    try:
        config = load_config()
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        raise typer.Exit(1)
    
    # Check if channel exists
    channel_cfg = getattr(config.channels, channel, None)
    if not channel_cfg or not channel_cfg.get("enabled"):
        console.print(f"[yellow]⚠[/yellow]  {channel.title()} channel is not configured")
        return
    
    # Confirm removal
    confirm = typer.confirm(f"Remove {channel.title()} channel configuration?", default=False)
    if not confirm:
        console.print("Cancelled")
        return
    
    # Remove channel config
    channel_cfg["enabled"] = False
    
    # Save
    try:
        save_config(config)
        console.print(f"[green]✓[/green] {channel.title()} channel removed")
    except Exception as e:
        console.print(f"[red]Error saving config:[/red] {e}")
        raise typer.Exit(1)


@channels_app.command("login")
def login(
    channel: str = typer.Argument(..., help="Channel type"),
):
    """Link channel account (for channels that support it)"""
    console.print(f"[cyan]Linking {channel} account...[/cyan]\n")
    
    if channel == "whatsapp":
        console.print("[cyan]WhatsApp QR login flow:[/cyan]")
        console.print("  1. Start Gateway with WhatsApp enabled")
        console.print("  2. Gateway will display a QR code")
        console.print("  3. Scan QR code with WhatsApp mobile app")
        console.print("  4. Account will be linked automatically\n")
        console.print("[yellow]Note:[/yellow] WhatsApp requires Node runtime and additional dependencies")
        console.print("Run: openclaw gateway run")
    else:
        console.print(f"[yellow]⚠[/yellow]  {channel.title()} does not support login flow")
        console.print(f"Configure with: openclaw channels add {channel}")


@channels_app.command("logout")
def logout(
    channel: str = typer.Option("telegram", "--channel", help="Channel to logout"),
    account: str = typer.Option(None, "--account", help="Account id"),
):
    """Log out of a channel session"""
    console.print(f"[yellow]Logging out from {channel}...[/yellow]")
    console.print("[yellow]⚠[/yellow]  Channel logout not yet implemented")


@channels_app.command("capabilities")
def capabilities(
    channel: str = typer.Option(None, "--channel", help="Channel name"),
    account: str = typer.Option(None, "--account", help="Account id"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show provider capabilities"""
    console.print("[yellow]⚠[/yellow]  Channel capabilities not yet implemented")


@channels_app.command("resolve")
def resolve(
    entries: list[str] = typer.Argument(..., help="Entries to resolve"),
    channel: str = typer.Option(None, "--channel", help="Channel name"),
    account: str = typer.Option(None, "--account", help="Account id"),
    kind: str = typer.Option("auto", "--kind", help="Target kind (auto|user|group)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Resolve channel/user names to IDs"""
    console.print("[yellow]⚠[/yellow]  Channel resolution not yet implemented")
    console.print(f"Would resolve: {', '.join(entries)}")


@channels_app.command("logs")
def logs(
    channel: str = typer.Option("all", "--channel", help="Channel filter"),
    lines: int = typer.Option(200, "--lines", help="Number of lines"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show recent channel logs"""
    console.print("[yellow]⚠[/yellow]  Channel logs not yet implemented")
    console.print(f"Would show {lines} lines for {channel}")
