"""Hooks management commands"""

import typer
from rich.console import Console

console = Console()
hooks_app = typer.Typer(help="Lifecycle hooks")


@hooks_app.command("list")
def list_hooks(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """List registered hooks"""
    try:
        from ..hooks.registry import get_hook_registry
        
        registry = get_hook_registry()
        hooks = registry.list_hooks() if hasattr(registry, 'list_hooks') else []
        
        if json_output:
            console.print(json.dumps({"hooks": hooks}, indent=2))
            return
        
        if not hooks:
            console.print("[yellow]No hooks registered[/yellow]")
            return
        
        console.print(f"[cyan]Registered Hooks ({len(hooks)}):[/cyan]")
        for hook in hooks:
            console.print(f"  • {hook}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@hooks_app.command("test")
def test(
    hook_name: str = typer.Argument(..., help="Hook name to test"),
    data: str = typer.Option("{}", "--data", help="Test data (JSON)"),
):
    """Test a hook"""
    console.print("[yellow]⚠[/yellow]  Hook testing not yet implemented")
    console.print(f"Would test hook: {hook_name}")


# Default action
@hooks_app.callback(invoke_without_command=True)
def hooks_default(ctx: typer.Context):
    """List hooks (default command)"""
    if ctx.invoked_subcommand is None:
        list_hooks()
