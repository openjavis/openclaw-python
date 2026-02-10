"""OpenClaw CLI - Unified command-line interface"""

import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..config.loader import load_config

app = typer.Typer(
    name="openclaw",
    help="🦞 OpenClaw - Personal AI Assistant Platform",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


@app.command()
def start(
    port: int = typer.Option(8765, "--port", "-p", help="WebSocket port for gateway"),
    telegram: bool = typer.Option(True, "--telegram/--no-telegram", help="Enable Telegram channel"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
):
    """
    Start OpenClaw server with all features (Gateway + Channels)
    """
    console.print(Panel.fit(
        "🦞 [bold cyan]OpenClaw Python[/bold cyan]\n"
        "Starting full-featured server...",
        border_style="cyan"
    ))
    
    # Load .env file before checking environment variables
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try workspace root
        workspace_root = Path(__file__).parent.parent.parent
        env_path = workspace_root / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    
    # Check environment
    issues = []
    if not any([os.getenv("ANTHROPIC_API_KEY"), os.getenv("OPENAI_API_KEY"), os.getenv("GOOGLE_API_KEY")]):
        issues.append("❌ No LLM API key found")
    
    if telegram and not os.getenv("TELEGRAM_BOT_TOKEN"):
        issues.append("⚠️  TELEGRAM_BOT_TOKEN not set")
        telegram = False
    
    if issues:
        console.print("\n[yellow]Configuration Issues:[/yellow]")
        for issue in issues:
            console.print(f"  {issue}")
        if any("❌" in issue for issue in issues):
            console.print("\n[red]Cannot start without an LLM API key.[/red]")
            raise typer.Exit(1)
    
    # Start server
    try:
        from ..monitoring import setup_logging
        setup_logging(level=log_level.upper())
        
        console.print("[green]✓[/green] Starting Gateway + Telegram...")
        
        # Use GatewayBootstrap to initialize and start all components
        import asyncio
        from ..gateway.bootstrap import GatewayBootstrap
        
        async def start_gateway():
            bootstrap = GatewayBootstrap()
            results = await bootstrap.bootstrap()
            
            # Keep running
            console.print(f"\n[green]✓[/green] Gateway running on ws://127.0.0.1:{results.get('gateway_port', 18789)}")
            console.print("[dim]Press Ctrl+C to stop[/dim]\n")
            
            # Keep alive until Ctrl+C
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Shutting down...[/yellow]")
                await bootstrap.shutdown()
        
        asyncio.run(start_gateway())
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Shutting down...[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def version():
    """Show OpenClaw version"""
    from openclaw import __version__
    console.print(f"[cyan]OpenClaw Python[/cyan] v{__version__}")


@app.command()
def doctor(
    repair: bool = typer.Option(
        False,
        "--repair",
        "--fix",
        help="Apply recommended fixes automatically"
    ),
    deep: bool = typer.Option(
        False,
        "--deep",
        help="Deep system scan (checks Gateway, channels, etc.)"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON"
    ),
):
    """Run diagnostics and check configuration"""
    console.print("[cyan]Running diagnostics...[/cyan]\n")

    issues = []
    warnings = []
    fixes = []
    check_results = []

    # Check 1: Python version
    py_version = sys.version_info
    if py_version < (3, 11):
        issues.append(
            f"Python {py_version.major}.{py_version.minor} is not supported. "
            "Please upgrade to Python 3.11+"
        )
        check_results.append({
            "check": "python_version",
            "status": "error",
            "message": f"Python {py_version.major}.{py_version.minor} < 3.11",
        })
    else:
        console.print(
            f"[green]✓[/green] Python {py_version.major}.{py_version.minor}.{py_version.micro}"
        )
        check_results.append({
            "check": "python_version",
            "status": "ok",
            "message": f"{py_version.major}.{py_version.minor}.{py_version.micro}",
        })

    # Check 2: Config file
    from ..config.loader import get_config_path, load_config

    config_path = get_config_path()
    if not config_path.exists():
        warnings.append(f"Config file not found at {config_path}")
        fixes.append(("create_config", "openclaw onboard"))
        console.print(f"[yellow]⚠[/yellow]  Config file not found")
        console.print(f"    Run: openclaw onboard")
        check_results.append({
            "check": "config_file",
            "status": "warning",
            "message": "not found",
            "fix": "openclaw onboard",
        })
    else:
        console.print(f"[green]✓[/green] Config file: {config_path}")

        # Try loading config
        try:
            config = load_config()
            console.print("[green]✓[/green] Config file is valid")
            check_results.append({
                "check": "config_file",
                "status": "ok",
                "message": "valid",
            })
        except Exception as e:
            issues.append(f"Config file is invalid: {e}")
            fixes.append(("fix_config", "openclaw configure"))
            console.print(f"[red]✗[/red] Config file is invalid: {e}")
            check_results.append({
                "check": "config_file",
                "status": "error",
                "message": str(e),
                "fix": "openclaw configure",
            })

    # Check 3: Workspace
    workspace = Path.home() / ".openclaw"
    if not workspace.exists():
        warnings.append(f"Workspace not found at {workspace}")
        fixes.append(("create_workspace", f"mkdir -p {workspace}"))
        console.print(f"[yellow]⚠[/yellow]  Workspace not found")
        
        if repair:
            workspace.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓[/green] Created workspace: {workspace}")
        else:
            console.print(f"    Run with --repair to create")
        
        check_results.append({
            "check": "workspace",
            "status": "warning",
            "message": "not found",
            "fix": f"mkdir -p {workspace}",
        })
    else:
        console.print(f"[green]✓[/green] Workspace: {workspace}")
        check_results.append({
            "check": "workspace",
            "status": "ok",
            "message": str(workspace),
        })

    # Check 4: Dependencies
    try:
        import anthropic
        console.print("[green]✓[/green] anthropic package installed")
        check_results.append({"check": "anthropic", "status": "ok"})
    except ImportError:
        warnings.append("anthropic package not installed")
        fixes.append(("install_anthropic", "uv add anthropic"))
        console.print("[yellow]⚠[/yellow]  anthropic package not installed")
        check_results.append({
            "check": "anthropic",
            "status": "warning",
            "fix": "uv add anthropic",
        })

    # Deep checks (if requested)
    if deep:
        console.print("\n[cyan]Running deep checks...[/cyan]")

        # Check 5: Gateway status
        try:
            from ..daemon.service import get_service_status
            status = get_service_status()
            
            if status["installed"]:
                if status["running"]:
                    console.print("[green]✓[/green] Gateway service is running")
                    check_results.append({
                        "check": "gateway_service",
                        "status": "ok",
                        "message": "running",
                    })
                else:
                    warnings.append("Gateway service installed but not running")
                    fixes.append(("start_gateway", "openclaw gateway start"))
                    console.print("[yellow]⚠[/yellow]  Gateway service not running")
                    console.print("    Run: openclaw gateway start")
                    check_results.append({
                        "check": "gateway_service",
                        "status": "warning",
                        "message": "not running",
                        "fix": "openclaw gateway start",
                    })
            else:
                console.print("[yellow]⚠[/yellow]  Gateway service not installed")
                console.print("    Run: openclaw gateway install")
                check_results.append({
                    "check": "gateway_service",
                    "status": "info",
                    "message": "not installed",
                    "fix": "openclaw gateway install",
                })
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow]  Could not check Gateway status: {e}")

        # Check 6: Channel credentials
        if config_path.exists():
            try:
                config = load_config()
                
                for channel_name in ["telegram", "discord", "slack"]:
                    channel_cfg = getattr(config.channels, channel_name, None)
                    if channel_cfg and channel_cfg.get("enabled"):
                        bot_token = channel_cfg.get("bot_token")
                        if bot_token:
                            console.print(f"[green]✓[/green] {channel_name.title()} credentials configured")
                            check_results.append({
                                "check": f"{channel_name}_credentials",
                                "status": "ok",
                            })
                        else:
                            warnings.append(f"{channel_name} enabled but no credentials")
                            console.print(f"[yellow]⚠[/yellow]  {channel_name.title()} enabled but no credentials")
                            check_results.append({
                                "check": f"{channel_name}_credentials",
                                "status": "warning",
                                "message": "no credentials",
                            })
            except Exception:
                pass

    # Apply automatic fixes if requested
    if repair and fixes and not json_output:
        console.print("\n[cyan]Applying fixes...[/cyan]")
        for fix_id, fix_cmd in fixes:
            if fix_id == "create_workspace":
                # Already handled above
                continue
            
            console.print(f"  To fix '{fix_id}', run: {fix_cmd}")

    # Summary
    console.print()
    if json_output:
        import json
        result = {
            "issues": len(issues),
            "warnings": len(warnings),
            "checks": check_results,
        }
        print(json.dumps(result, indent=2))
    else:
        if issues:
            console.print(f"[red]✗[/red] {len(issues)} issue(s) found:")
            for issue in issues:
                console.print(f"  - {issue}")
        if warnings:
            console.print(f"[yellow]⚠[/yellow]  {len(warnings)} warning(s):")
            for warning in warnings:
                console.print(f"  - {warning}")
        if not issues and not warnings:
            console.print("[green]✓[/green] All checks passed!")
        
        if fixes and not repair:
            console.print("\n[cyan]Suggested fixes:[/cyan]")
            console.print("  Run with --repair to apply fixes automatically")
            console.print("  Or run these commands manually:")
            for fix_id, fix_cmd in fixes:
                console.print(f"    {fix_cmd}")

    if issues:
        raise typer.Exit(1)


# Register subcommand modules
from .gateway_cmd import gateway_app
from .channels_cmd import channels_app
from .agent_cmd import agent_app
from .config_cmd import config_app
from .status_cmd import status_app
from .memory_cmd import memory_app
from .models_cmd import models_app
from .skills_cmd import skills_app
from .tools_cmd import tools_app
from .logs_cmd import logs_app
from .message_cmd import message_app
from .browser_cmd import browser_app
from .system_cmd import system_app
from .cron_cmd import cron_app
from .hooks_cmd import hooks_app
from .plugins_cmd import plugins_app
from .security_cmd import security_app
from .sandbox_cmd import sandbox_app
from .nodes_cmd import nodes_app
from .misc_cmd import register_misc_commands

app.add_typer(gateway_app, name="gateway")
app.add_typer(channels_app, name="channels")
app.add_typer(agent_app, name="agent")
app.add_typer(config_app, name="config")
app.add_typer(status_app, name="status")
app.add_typer(memory_app, name="memory")
app.add_typer(models_app, name="models")
app.add_typer(skills_app, name="skills")
app.add_typer(tools_app, name="tools")
app.add_typer(logs_app, name="logs")
app.add_typer(message_app, name="message")
app.add_typer(browser_app, name="browser")
app.add_typer(system_app, name="system")
app.add_typer(cron_app, name="cron")
app.add_typer(hooks_app, name="hooks")
app.add_typer(plugins_app, name="plugins")
app.add_typer(security_app, name="security")
app.add_typer(sandbox_app, name="sandbox")
app.add_typer(nodes_app, name="nodes")

# Register misc commands (tui, update, onboard, setup, configure, etc)
register_misc_commands(app)


def main():
    """CLI entry point"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
