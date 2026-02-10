"""Skills management commands"""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()
skills_app = typer.Typer(help="List and inspect available skills")


@skills_app.command("list")
def list_skills(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    eligible: bool = typer.Option(False, "--eligible", help="Show only eligible skills"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show more details"),
):
    """List all available skills"""
    try:
        from ..agents.skills.loader import load_skills_from_dir
        
        all_skills = []
        
        # Load from all sources
        project_root = Path(__file__).parent.parent.parent
        bundled_skills = project_root / "skills"
        managed_skills = Path.home() / ".openclaw" / "skills"
        workspace_skills = Path.home() / ".openclaw" / "workspace" / "skills"
        
        for skills_dir, source in [
            (bundled_skills, "bundled"),
            (managed_skills, "managed"),
            (workspace_skills, "workspace"),
        ]:
            if skills_dir.exists():
                loaded = load_skills_from_dir(skills_dir, source)
                all_skills.extend(loaded)
        
        # For now, show all skills (eligibility filtering can be added later)
        skills_to_show = all_skills
        
        if json_output:
            skills_data = [
                {
                    "name": skill.name,
                    "description": skill.description or "",
                    "source": skill.source,
                }
                for skill in skills_to_show
            ]
            console.print(json.dumps(skills_data, indent=2))
            return
        
        if not skills_to_show:
            console.print("[yellow]No skills found[/yellow]")
            return
        
        table = Table(title=f"Skills ({len(skills_to_show)})")
        table.add_column("Name", style="cyan")
        table.add_column("Source", style="yellow")
        table.add_column("Description", style="green")
        
        for skill in skills_to_show:
            desc = skill.description or ""
            if len(desc) > 60:
                desc = desc[:60] + "..."
            table.add_row(skill.name, skill.source, desc)
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@skills_app.command("info")
def info(
    name: str = typer.Argument(..., help="Skill name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Show detailed information about a skill"""
    try:
        from ..skills.loader import SkillLoader
        
        loader = SkillLoader()
        loader.load_all_skills()
        
        skill = loader.skills.get(name)
        if not skill:
            console.print(f"[red]Skill not found:[/red] {name}")
            raise typer.Exit(1)
        
        if json_output:
            skill_data = {
                "name": skill.name,
                "description": skill.metadata.description,
                "source": skill.source,
                "path": skill.path,
            }
            console.print(json.dumps(skill_data, indent=2))
            return
        
        console.print(f"\n[bold cyan]{skill.name}[/bold cyan]")
        console.print(f"[dim]Source: {skill.source}[/dim]")
        console.print(f"[dim]Path: {skill.path}[/dim]\n")
        console.print(skill.metadata.description)
        console.print()
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@skills_app.command("check")
def check(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
):
    """Check which skills are ready vs missing requirements"""
    try:
        from ..skills.loader import SkillLoader
        
        loader = SkillLoader()
        loader.load_all_skills()
        
        all_skills = list(loader.skills.values())
        eligible_skills = loader.get_eligible_skills()
        
        eligible_count = len(eligible_skills)
        total_count = len(all_skills)
        
        if json_output:
            result = {
                "total": total_count,
                "eligible": eligible_count,
                "ready": list(eligible_skills.keys()),
                "not_ready": [s.name for s in all_skills if s.name not in eligible_skills],
            }
            console.print(json.dumps(result, indent=2))
            return
        
        console.print(f"\n[cyan]Skills Status:[/cyan]")
        console.print(f"  Total: {total_count}")
        console.print(f"  [green]✓[/green] Ready: {eligible_count}")
        console.print(f"  [yellow]✗[/yellow] Not ready: {total_count - eligible_count}")
        
        if eligible_count > 0:
            console.print(f"\n[green]Ready skills:[/green]")
            for name in eligible_skills.keys():
                console.print(f"  • {name}")
        
        not_ready = [s for s in all_skills if s.name not in eligible_skills]
        if not_ready:
            console.print(f"\n[yellow]Not ready (may need dependencies):[/yellow]")
            for skill in not_ready:
                console.print(f"  • {skill.name}")
        
        console.print()
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


# Default action
@skills_app.callback(invoke_without_command=True)
def skills_default(ctx: typer.Context):
    """List skills (default command)"""
    if ctx.invoked_subcommand is None:
        list_skills()
