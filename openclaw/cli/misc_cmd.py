"""Miscellaneous commands (tui, update, etc)"""

import typer
from rich.console import Console

console = Console()


def register_misc_commands(app: typer.Typer):
    """Register miscellaneous commands to the main app"""
    
    @app.command("tui")
    def tui():
        """Launch Terminal UI"""
        try:
            import asyncio
            from ..tui.tui import run_tui
            console.print("[cyan]Launching Terminal UI...[/cyan]")
            asyncio.run(run_tui())
        except KeyboardInterrupt:
            console.print("\n[yellow]TUI stopped[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    @app.command("update")
    def update(
        check: bool = typer.Option(False, "--check", help="Check for updates only"),
        force: bool = typer.Option(False, "--force", help="Force update"),
    ):
        """Update OpenClaw"""
        console.print("[yellow]⚠[/yellow]  Update not yet implemented")
    
    @app.command("onboard")
    def onboard(
        install_daemon: bool = typer.Option(
            False,
            "--install-daemon",
            help="Install Gateway as system service after onboarding"
        ),
        non_interactive: bool = typer.Option(
            False,
            "--non-interactive",
            help="Non-interactive mode (use environment variables)"
        ),
        workspace: str = typer.Option(
            None,
            "--workspace",
            help="Workspace directory"
        ),
    ):
        """Run onboarding wizard"""
        try:
            import asyncio
            from pathlib import Path
            from ..wizard.onboarding import run_onboarding
            
            console.print("[cyan]Starting onboarding wizard...[/cyan]\n")
            
            workspace_dir = Path(workspace) if workspace else None
            
            result = asyncio.run(run_onboarding(
                workspace_dir=workspace_dir,
                install_daemon=install_daemon,
                non_interactive=non_interactive
            ))
            
            # Success message already printed by wizard
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Onboarding cancelled[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    @app.command("setup")
    def setup():
        """Run setup wizard"""
        console.print("[yellow]⚠[/yellow]  Setup wizard not yet implemented")
    
    @app.command("configure")
    def configure(
        section: str = typer.Option(
            None,
            "--section",
            help="Configuration section (gateway, channels, agents, tools, security)"
        ),
    ):
        """Run configuration wizard"""
        try:
            import asyncio
            from ..wizard.configure import run_configure_wizard
            
            console.print("[cyan]Starting configuration wizard...[/cyan]\n")
            result = asyncio.run(run_configure_wizard(section=section))
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Configuration cancelled[/yellow]")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
    
    @app.command("docs")
    def docs():
        """Open documentation"""
        console.print("[cyan]📚 Documentation:[/cyan]")
        console.print("https://github.com/your-org/openclaw-python")
    
    @app.command("webhooks")
    def webhooks():
        """Manage webhooks"""
        console.print("[yellow]⚠[/yellow]  Webhooks management not yet implemented")
    
    @app.command("directory")
    def directory():
        """Show OpenClaw directories"""
        from pathlib import Path
        console.print("[cyan]OpenClaw Directories:[/cyan]")
        console.print(f"  Config: {Path.home() / '.openclaw'}")
        console.print(f"  State: {Path.home() / '.openclaw' / 'state'}")
        console.print(f"  Logs: {Path.home() / '.openclaw' / 'logs'}")
    
    @app.command("completion")
    def completion():
        """Shell completion setup"""
        console.print("[yellow]⚠[/yellow]  Shell completion not yet implemented")
    
    @app.command("approvals")
    def approvals():
        """Manage approvals"""
        console.print("[yellow]⚠[/yellow]  Approvals management not yet implemented")
    
    @app.command("acp")
    def acp():
        """Approvals Control Panel"""
        console.print("[yellow]⚠[/yellow]  ACP not yet implemented")
