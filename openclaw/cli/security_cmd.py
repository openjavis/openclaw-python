"""Security and permissions commands"""

import typer
from rich.console import Console

console = Console()
security_app = typer.Typer(help="Security and permissions")


@security_app.command("status")
def status(json_output: bool = typer.Option(False, "--json", help="Output JSON")):
    """Show security status"""
    console.print("[yellow]⚠[/yellow]  Security status not yet implemented")


@security_app.command("audit")
def audit(
    deep: bool = typer.Option(False, "--deep", help="Deep scan"),
    fix: bool = typer.Option(False, "--fix", help="Apply security fixes"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
):
    """Run security audit"""
    from pathlib import Path
    from ..config.loader import load_config, get_config_path, save_config
    
    console.print("[cyan]Running security audit...[/cyan]\n")
    
    results = {
        "critical": [],
        "warnings": [],
        "info": [],
    }
    
    # Check 1: Config file permissions
    config_file = get_config_path()
    if config_file.exists():
        import stat
        st = config_file.stat()
        file_mode = st.st_mode & 0o777
        
        # Check if file is readable by others
        if file_mode & 0o077:
            results["warnings"].append({
                "check": "config_permissions",
                "message": f"Config file {config_file} has weak permissions: {oct(file_mode)}",
                "fix": f"chmod 600 {config_file}",
            })
            console.print(f"[yellow]⚠[/yellow]  Config file has weak permissions: {oct(file_mode)}")
            
            if fix:
                try:
                    config_file.chmod(0o600)
                    console.print(f"[green]✓[/green] Fixed: Set permissions to 600")
                except Exception as e:
                    console.print(f"[red]Error:[/red] Could not fix permissions: {e}")
        else:
            console.print(f"[green]✓[/green] Config file permissions OK: {oct(file_mode)}")
    
    # Check 2: Gateway authentication
    try:
        config = load_config()
        
        if config.gateway and config.gateway.auth:
            auth_mode = config.gateway.auth.mode
            
            if auth_mode == "none":
                results["critical"].append({
                    "check": "gateway_auth",
                    "message": "Gateway has no authentication",
                    "fix": "Configure token or password auth: openclaw configure --section gateway",
                })
                console.print("[red]✗[/red] Gateway has no authentication")
            elif auth_mode == "token":
                token = config.gateway.auth.token
                if not token:
                    results["critical"].append({
                        "check": "gateway_token",
                        "message": "Gateway token not set",
                        "fix": "Generate token: openclaw gateway generate-token",
                    })
                    console.print("[red]✗[/red] Gateway token not set")
                elif len(token) < 32:
                    results["warnings"].append({
                        "check": "gateway_token",
                        "message": "Gateway token is weak (< 32 characters)",
                        "fix": "Generate strong token: openclaw gateway generate-token",
                    })
                    console.print("[yellow]⚠[/yellow]  Gateway token is weak")
                else:
                    console.print("[green]✓[/green] Gateway token is secure")
            elif auth_mode == "password":
                password = config.gateway.auth.password
                if not password:
                    results["critical"].append({
                        "check": "gateway_password",
                        "message": "Gateway password not set",
                        "fix": "Set password: openclaw configure --section gateway",
                    })
                    console.print("[red]✗[/red] Gateway password not set")
                elif len(password) < 12:
                    results["warnings"].append({
                        "check": "gateway_password",
                        "message": "Gateway password is weak (< 12 characters)",
                        "fix": "Set stronger password: openclaw configure --section gateway",
                    })
                    console.print("[yellow]⚠[/yellow]  Gateway password is weak")
                else:
                    console.print("[green]✓[/green] Gateway password is secure")
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
    
    # Check 3: Channel DM policies
    try:
        config = load_config()
        
        for channel_name in ["telegram", "discord", "slack"]:
            channel_cfg = getattr(config.channels, channel_name, None)
            if channel_cfg and channel_cfg.get("enabled"):
                dm_policy = channel_cfg.get("dmPolicy") or channel_cfg.get("dm_policy", "open")
                
                if dm_policy == "open":
                    results["warnings"].append({
                        "check": f"{channel_name}_dm_policy",
                        "message": f"{channel_name.title()} has open DM policy",
                        "fix": f"Set dmPolicy to 'pairing' or 'allowlist' in config",
                    })
                    console.print(f"[yellow]⚠[/yellow]  {channel_name.title()} has open DM policy")
                else:
                    console.print(f"[green]✓[/green] {channel_name.title()} DM policy: {dm_policy}")
    except Exception:
        pass
    
    # Check 4: Bash execution security (deep scan)
    if deep:
        console.print("\n[cyan]Deep scan...[/cyan]")
        
        try:
            config = load_config()
            
            if config.tools and config.tools.exec:
                security_mode = config.tools.exec.security
                
                if security_mode == "full":
                    results["info"].append({
                        "check": "bash_security",
                        "message": "Bash execution has full access",
                        "info": "This is powerful but can be risky. Consider 'allowlist' mode.",
                    })
                    console.print("[cyan]ℹ[/cyan]  Bash execution: full access (powerful but risky)")
                elif security_mode == "deny":
                    console.print("[green]✓[/green] Bash execution: denied")
                else:
                    console.print(f"[green]✓[/green] Bash execution: {security_mode}")
        except Exception:
            pass
    
    # Check 5: API keys in config (deep scan)
    if deep:
        try:
            config_dict = config.model_dump()
            
            # Check if API keys are in config file (they should be in .env instead)
            api_key_fields = ["api_key", "apiKey", "bot_token", "botToken"]
            found_keys = []
            
            def check_dict(d, path=""):
                for key, value in d.items():
                    if key in api_key_fields and value:
                        found_keys.append(f"{path}.{key}" if path else key)
                    if isinstance(value, dict):
                        check_dict(value, f"{path}.{key}" if path else key)
            
            check_dict(config_dict)
            
            if found_keys:
                results["warnings"].append({
                    "check": "api_keys_in_config",
                    "message": f"API keys found in config file: {', '.join(found_keys)}",
                    "fix": "Move API keys to .env file for better security",
                })
                console.print("[yellow]⚠[/yellow]  API keys found in config file")
                console.print("    Recommendation: Move to .env file")
        except Exception:
            pass
    
    # Summary
    console.print()
    if json_output:
        import json
        print(json.dumps(results, indent=2))
    else:
        if results["critical"]:
            console.print(f"[red]✗[/red] {len(results['critical'])} critical issue(s):")
            for item in results["critical"]:
                console.print(f"  - {item['message']}")
                if "fix" in item:
                    console.print(f"    Fix: {item['fix']}")
        
        if results["warnings"]:
            console.print(f"[yellow]⚠[/yellow]  {len(results['warnings'])} warning(s):")
            for item in results["warnings"]:
                console.print(f"  - {item['message']}")
                if "fix" in item:
                    console.print(f"    Fix: {item['fix']}")
        
        if results["info"]:
            console.print(f"[cyan]ℹ[/cyan]  {len(results['info'])} info:")
            for item in results["info"]:
                console.print(f"  - {item['message']}")
                if "info" in item:
                    console.print(f"    {item['info']}")
        
        if not results["critical"] and not results["warnings"]:
            console.print("[green]✓[/green] No security issues found!")
        
        if fix:
            console.print("\n[cyan]Applied automatic fixes where possible[/cyan]")
    
    if results["critical"] and not json_output:
        raise typer.Exit(1)
