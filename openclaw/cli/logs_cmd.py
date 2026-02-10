"""Gateway logs command"""

import json

import typer
from rich.console import Console

console = Console()
logs_app = typer.Typer(help="Gateway file logs", no_args_is_help=False)


@logs_app.callback(invoke_without_command=True)
def logs(
    ctx: typer.Context,
    limit: int = typer.Option(200, "--limit", help="Max lines to return"),
    max_bytes: int = typer.Option(250000, "--max-bytes", help="Max bytes to read"),
    follow: bool = typer.Option(False, "--follow", help="Follow log output"),
    interval: int = typer.Option(1000, "--interval", help="Polling interval in ms"),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON log lines"),
    plain: bool = typer.Option(False, "--plain", help="Plain text output (no ANSI)"),
):
    """Tail gateway file logs"""
    if ctx.invoked_subcommand is not None:
        return
    
    try:
        import time
        
        log_file = Path.home() / ".openclaw" / "logs" / "gateway.log"
        
        if not log_file.exists():
            console.print("[yellow]Log file not found[/yellow]")
            console.print(f"Expected at: {log_file}")
            return
        
        if json_output:
            with open(log_file) as f:
                lines = f.readlines()[-limit:]
            for line in lines:
                console.print(line.rstrip())
            return
        
        console.print(f"[dim]Tailing {log_file}[/dim]\n")
        
        with open(log_file) as f:
            # Seek to end minus limit lines
            lines = f.readlines()[-limit:]
            for line in lines:
                console.print(line.rstrip())
        
        if follow:
            console.print(f"\n[dim]Following (Ctrl+C to stop)...[/dim]\n")
            try:
                with open(log_file) as f:
                    f.seek(0, 2)  # Seek to end
                    while True:
                        line = f.readline()
                        if line:
                            console.print(line.rstrip())
                        else:
                            time.sleep(interval / 1000.0)
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopped[/yellow]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
