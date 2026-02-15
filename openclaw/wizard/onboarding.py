"""Onboarding wizard

First-run onboarding experience for new users.
Matches TypeScript openclaw/src/wizard/onboarding.ts
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config.loader import load_config, save_config
from ..config.schema import ClawdbotConfig, AgentConfig, GatewayConfig, ChannelsConfig, AuthConfig
from .auth import configure_auth, check_env_api_key
from .config import configure_telegram_enhanced, configure_discord_enhanced, configure_agent

logger = logging.getLogger(__name__)


async def check_gateway_health(port: int = 18789, token: Optional[str] = None) -> dict:
    """Check if Gateway is reachable and healthy
    
    Args:
        port: Gateway port
        token: Authentication token (if required)
    
    Returns:
        Dict with 'ok' (bool) and 'detail' (str) keys
    """
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            
            response = await client.get(
                f"http://localhost:{port}/health",
                headers=headers
            )
            response.raise_for_status()
            return {"ok": True, "detail": "Gateway reachable"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


async def run_onboarding_wizard(
    config: Optional[dict] = None,
    workspace_dir: Optional[Path] = None,
    install_daemon: Optional[bool] = None,
    skip_health: bool = False,
    skip_ui: bool = False,
    non_interactive: bool = False,
    accept_risk: bool = False,
    flow: Optional[str] = None,
) -> dict:
    """
    Run onboarding wizard
    
    Guides new users through initial setup:
    - Risk confirmation
    - Mode selection (QuickStart/Advanced)
    - API key configuration
    - Model selection
    - Gateway configuration
    - Channel setup
    - Gateway service installation (optional)
    
    Args:
        config: Existing Gateway configuration (optional)
        workspace_dir: Workspace directory (optional)
        install_daemon: Whether to install Gateway service (None=auto-decide based on flow)
        skip_health: Skip health check after installation
        skip_ui: Skip UI selection prompts
        non_interactive: Run without prompts (requires accept_risk=True)
        accept_risk: Accept risk acknowledgement
        flow: Onboarding flow type: "quickstart" or "advanced"
        
    Returns:
        Dict with wizard results
    """
    logger.info("Starting onboarding wizard")
    
    print("\n" + "=" * 80)
    print("🚀 Welcome to OpenClaw Onboarding!")
    print("=" * 80)
    print("\nThis wizard will help you set up OpenClaw for the first time.")
    print("You can exit anytime with Ctrl+C")
    
    # Step 1: Risk confirmation
    if non_interactive:
        if not accept_risk:
            print("[red]Error:[/red] --accept-risk is required for --non-interactive mode")
            return {"completed": False, "skipped": True, "reason": "Risk not accepted"}
    else:
        if not _confirm_risks():
            return {"completed": False, "skipped": True, "reason": "User declined"}
    
    # Step 2: Mode selection
    if flow:
        flow_normalized = flow.lower().strip()
        if flow_normalized in ["quickstart", "advanced"]:
            mode = flow_normalized
            print(f"\n✓ Using {mode} mode")
        else:
            print(f"[yellow]Warning:[/yellow] Invalid --flow value '{flow}'. Using interactive mode selection.")
            mode = _select_mode()
    else:
        mode = _select_mode()
    
    # Step 3: Load or create config
    try:
        existing_config_dict = load_config(as_dict=True)
        print("\n✓ Found existing configuration")
        
        if mode == "quickstart":
            print("QuickStart mode: Using existing configuration as base")
            # Convert dict to ClawdbotConfig object
            claw_config = ClawdbotConfig(**existing_config_dict) if existing_config_dict else ClawdbotConfig()
        else:
            action = _prompt_config_action()
            if action == "reset":
                print("Creating fresh configuration...")
                claw_config = ClawdbotConfig()
            elif action == "modify":
                print("Modifying existing configuration...")
                # Convert dict to ClawdbotConfig object
                claw_config = ClawdbotConfig(**existing_config_dict) if existing_config_dict else ClawdbotConfig()
            else:  # keep
                print("Keeping existing configuration...")
                return {"completed": True, "skipped": False, "kept_existing": True}
    except Exception as e:
        logger.info(f"No existing config: {e}")
        print("\nCreating new configuration...")
        claw_config = ClawdbotConfig()
    
    # Step 4: Provider configuration
    provider_config = await _configure_provider(mode)
    if provider_config:
        # Update agent config with provider
        if not claw_config.agent:
            claw_config.agent = AgentConfig()
        claw_config.agent.model = provider_config.get("model", "claude-sonnet-4")
        # Store auth in environment variables (handled by configure_auth)
    
    # Step 5: Agent configuration
    if mode == "advanced":
        agent_config = await _configure_agent_settings()
        if agent_config:
            if not claw_config.agent:
                claw_config.agent = AgentConfig()
            claw_config.agent.workspace = agent_config.get("workspace", "./workspace")
    
    # Step 6: Gateway configuration
    gateway_config = await _configure_gateway(mode)
    if gateway_config:
        if not claw_config.gateway:
            claw_config.gateway = GatewayConfig()
        claw_config.gateway.port = gateway_config.get("port", 18789)
        claw_config.gateway.bind = gateway_config.get("bind", "loopback")
        
        # Handle authentication properly
        if "auth_token" in gateway_config or "auth_password" in gateway_config:
            if not claw_config.gateway.auth:
                claw_config.gateway.auth = AuthConfig()
            
            if "auth_token" in gateway_config:
                claw_config.gateway.auth.token = gateway_config["auth_token"]
                claw_config.gateway.auth.mode = "token"
            if "auth_password" in gateway_config:
                claw_config.gateway.auth.password = gateway_config["auth_password"]
                claw_config.gateway.auth.mode = "password"
    
    # Step 7: Channels configuration
    channels_config = await _configure_channels(mode)
    if channels_config:
        if not claw_config.channels:
            claw_config.channels = ChannelsConfig()
        if "telegram" in channels_config:
            claw_config.channels.telegram = channels_config["telegram"]
        if "discord" in channels_config:
            claw_config.channels.discord = channels_config["discord"]
    
    # Step 7.5: Collect user information for workspace
    user_info = {}
    if not non_interactive and (mode == "advanced" or mode == "quickstart"):
        print("\n" + "-" * 80)
        print("User Profile Setup")
        print("-" * 80)
        print("\nLet's personalize your experience.")
        
        # User name
        user_name = input("\nWhat's your name? [Optional, press Enter to skip]: ").strip()
        if user_name:
            user_info["name"] = user_name
            user_info["what_to_call_them"] = input(f"How should the agent address you? [{user_name}]: ").strip() or user_name
        
        # Timezone
        import datetime
        try:
            local_tz = datetime.datetime.now().astimezone().tzinfo
            tz_str = str(local_tz)
        except Exception:
            tz_str = "UTC"
        
        user_timezone = input(f"Your timezone? [{tz_str}]: ").strip() or tz_str
        user_info["timezone"] = user_timezone
        
        # Agent personality preference
        print("\nWhat kind of agent personality do you prefer?")
        print("  1. Professional - Formal and focused")
        print("  2. Friendly - Warm and conversational")
        print("  3. Concise - Brief and to the point")
        print("  4. Custom - I'll configure it later")
        
        personality_choice = input("\nSelect [2]: ").strip() or "2"
        personality_map = {
            "1": "professional",
            "2": "friendly",
            "3": "concise",
            "4": "custom"
        }
        user_info["preferred_vibe"] = personality_map.get(personality_choice, "friendly")
    
    # Store user info for later use
    if user_info:
        # Store in a temporary attribute on config
        claw_config._user_info = user_info
    
    # Step 8: Save configuration
    print("\n" + "-" * 80)
    print("Configuration Summary:")
    print("-" * 80)
    print(f"Provider: {provider_config.get('provider', 'Not configured')}")
    print(f"Model: {claw_config.agent.model if claw_config.agent else 'Default'}")
    print(f"Gateway Port: {claw_config.gateway.port if claw_config.gateway else 18789}")
    print(f"Gateway Bind: {claw_config.gateway.bind if claw_config.gateway else 'loopback'}")
    if channels_config:
        if "telegram" in channels_config:
            print("✓ Telegram configured")
        if "discord" in channels_config:
            print("✓ Discord configured")
    print("-" * 80)
    
    save_choice = input("\nSave this configuration? [Y/n]: ").strip().lower()
    if save_choice == "n":
        print("Configuration not saved. Exiting...")
        return {"completed": False, "skipped": True, "reason": "User chose not to save"}
    
    try:
        save_config(claw_config)
        print("✓ Configuration saved!")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        print(f"✗ Error saving configuration: {e}")
        return {"completed": False, "error": str(e)}
    
    # Step 9: Mark onboarding complete
    if workspace_dir:
        mark_onboarding_complete(workspace_dir)
    else:
        mark_onboarding_complete(Path.home() / ".openclaw")
    
    # Step 9.3: Populate workspace with user information
    if hasattr(claw_config, '_user_info') and claw_config._user_info:
        print("\n" + "~" * 60)
        print("Personalizing workspace...")
        print("~" * 60)
        
        try:
            from ..agents.populate_workspace import populate_user_md, populate_soul_md, populate_identity_md
            from ..agents.ensure_workspace import ensure_agent_workspace
            
            # Determine workspace directory
            ws_dir = workspace_dir or (Path.home() / ".openclaw" / "workspace")
            
            # Ensure workspace exists
            ensure_agent_workspace(
                workspace_dir=ws_dir,
                ensure_bootstrap_files=True,
                skip_bootstrap=False
            )
            
            # Write user info
            populate_user_md(ws_dir, claw_config._user_info)
            print("✓ Created USER.md with your information")
            
            # Update SOUL.md with vibe
            if "preferred_vibe" in claw_config._user_info:
                populate_soul_md(ws_dir, claw_config._user_info["preferred_vibe"])
                print("✓ Updated SOUL.md with your preferences")
            
            # Create IDENTITY.md placeholder
            populate_identity_md(ws_dir)
            print("✓ Created IDENTITY.md template")
            
            print(f"\n✓ Workspace files created at: {ws_dir}")
            print("  You can edit these files anytime to customize your agent's behavior.")
            
        except Exception as e:
            logger.warning(f"Failed to populate workspace: {e}")
            print("⚠ Could not auto-populate workspace files")
            print(f"  You can manually edit files in: {ws_dir if 'ws_dir' in locals() else workspace_dir}")
    
    # Step 9.5: Install Gateway service (if requested)
    gateway_installed = False
    gateway_running = False
    
    # Determine if we should install daemon
    should_install_daemon = install_daemon
    if should_install_daemon is None:
        # Auto-decide based on flow: quickstart installs by default
        should_install_daemon = (mode == "quickstart")
    
    if should_install_daemon:
        print("\n" + "~" * 60)
        print("Installing Gateway Service...")
        print("~" * 60)
        
        try:
            from ..daemon.service import get_service_manager
            manager = get_service_manager("openclaw")
            
            # Check if already installed
            if manager.is_installed():
                if non_interactive or mode == "quickstart":
                    action = "R"  # Auto-restart in non-interactive/quickstart
                    print("Gateway service already installed. Restarting...")
                else:
                    action = input("\nGateway service already installed. [R]estart / Re[i]nstall / [S]kip? [R]: ").strip().upper() or "R"
                
                if action == "I":
                    print("Uninstalling existing service...")
                    manager.uninstall()
                    gateway_installed = False
                elif action == "S":
                    print("Skipping Gateway service installation")
                    should_install_daemon = False
                    gateway_installed = True
                    # Check if it's running
                    gateway_running = manager.is_running()
                elif action == "R":
                    print("Restarting Gateway service...")
                    try:
                        manager.restart()
                        print("✓ Gateway service restarted")
                        gateway_installed = True
                        gateway_running = True
                    except Exception as e:
                        logger.error(f"Failed to restart Gateway: {e}")
                        print(f"✗ Gateway restart failed: {e}")
                        gateway_running = False
            
            if should_install_daemon and not gateway_installed:
                print("Installing Gateway service...")
                manager.install()
                print("✓ Gateway service installed")
                gateway_installed = True
                
                # Start the service
                print("Starting Gateway service...")
                try:
                    manager.start()
                    print("✓ Gateway service started")
                    gateway_running = True
                except Exception as e:
                    logger.error(f"Failed to start Gateway: {e}")
                    print(f"✗ Gateway start failed: {e}")
                    print("You can start it manually with:")
                    print("  $ uv run openclaw gateway start")
                    gateway_running = False
                    
        except Exception as e:
            logger.error(f"Failed to install/start Gateway: {e}")
            print(f"✗ Gateway service installation failed: {e}")
            print("\nYou can install it manually later with:")
            print("  $ uv run openclaw gateway install")
            print("  $ uv run openclaw gateway start")
            gateway_installed = False
            gateway_running = False
    
    # Step 9.6: Health check
    gateway_port = claw_config.gateway.port if claw_config.gateway else 18789
    gateway_token = None
    if claw_config.gateway and claw_config.gateway.auth:
        gateway_token = claw_config.gateway.auth.token
    
    if not skip_health and gateway_running:
        print("\nRunning health check...")
        
        # Wait a bit for service to start
        import asyncio
        await asyncio.sleep(2)
        
        health = await check_gateway_health(
            port=gateway_port,
            token=gateway_token
        )
        
        if health["ok"]:
            print("✓ Gateway is healthy")
        else:
            print(f"⚠ Gateway health check failed: {health['detail']}")
            print("Troubleshooting: https://docs.openclaw.ai/gateway/troubleshooting")
    
    # Step 9.7: UI selection prompt (optional, for advanced mode)
    if not skip_ui and gateway_running and mode == "advanced" and not non_interactive:
        print("\n" + "~" * 60)
        print("How would you like to start?")
        print("~" * 60)
        print("  1. Open Web UI (recommended)")
        print("  2. Start interactive chat")
        print("  3. Do this later")
        
        choice = input("\nSelect option [1]: ").strip() or "1"
        
        if choice == "1":
            import webbrowser
            url = f"http://localhost:{gateway_port}"
            print(f"\nOpening {url} in your browser...")
            if webbrowser.open(url):
                print("✓ Opened Web UI in your browser")
            else:
                print(f"⚠ Could not open browser automatically. Please visit: {url}")
        elif choice == "2":
            print("\n💬 Interactive chat mode:")
            print("Use the following command to start chatting:")
            print(f"  $ uv run openclaw chat --interactive")
            print("\nOr send a single message:")
            print(f"  $ uv run openclaw chat 'Hello!'")
        else:
            print("\n✓ You can access the Web UI anytime:")
            print(f"  http://localhost:{gateway_port}")
    
    # Step 10: Display comprehensive next steps
    print("\n" + "=" * 80)
    print("🎉 Onboarding Complete!")
    print("=" * 80)
    
    # Gateway information
    gateway_port = claw_config.gateway.port if claw_config.gateway else 18789
    gateway_token = None
    if claw_config.gateway and claw_config.gateway.auth:
        gateway_token = claw_config.gateway.auth.token
    
    print("\n📡 Gateway Information:")
    print(f"  Port: {gateway_port}")
    print(f"  Web UI: http://localhost:{gateway_port}")
    print(f"  WebSocket: ws://localhost:{gateway_port}")
    if gateway_token:
        print(f"  Auth token: {gateway_token[:20]}... (stored in config)")
        print(f"  View full token: uv run openclaw config get gateway.auth.token")
    
    # Service status
    if gateway_installed and gateway_running:
        print("\n✓ Gateway service: Installed and Running")
        print("  Manage with:")
        print("    $ uv run openclaw gateway status")
        print("    $ uv run openclaw gateway stop")
        print("    $ uv run openclaw gateway restart")
    elif gateway_installed:
        print("\n⚠ Gateway service: Installed but not running")
        print("  Start with:")
        print("    $ uv run openclaw gateway start")
    else:
        print("\n⚠ Gateway service: Not installed")
        print("  Install with:")
        print("    $ uv run openclaw gateway install")
        print("    $ uv run openclaw gateway start")
    
    # Channels
    if channels_config:
        print("\n📱 Configured Channels:")
        if "telegram" in channels_config:
            print("  ✓ Telegram - Open Telegram and message your bot")
        if "discord" in channels_config:
            print("  ✓ Discord - Invite your bot to a server")
    
    # Next steps
    print("\n🚀 Next Steps:")
    if not gateway_running:
        print("  1. Start the Gateway:")
        print("     $ uv run openclaw gateway start")
        print()
        print("  2. Open the Control UI:")
        print(f"     http://localhost:{gateway_port}")
        if gateway_token:
            print("     (Paste the auth token if prompted)")
    else:
        print(f"  1. Open the Control UI: http://localhost:{gateway_port}")
        if gateway_token:
            print("     (Paste the auth token if prompted)")
        print()
        print("  2. Or use the CLI:")
        print("     $ uv run openclaw chat 'Hello!'")
        print("     $ uv run openclaw chat --interactive")
    
    print("\n📚 Documentation:")
    print("  Getting started: https://docs.openclaw.ai/getting-started")
    print("  Configuration:   https://docs.openclaw.ai/gateway/configuration")
    print("  Security:        https://docs.openclaw.ai/security")
    print("  Troubleshooting: https://docs.openclaw.ai/gateway/troubleshooting")
    
    print("\n💡 Useful Commands:")
    print("  View config:     uv run openclaw config show")
    print("  Health check:    uv run openclaw doctor")
    print("  List channels:   uv run openclaw channels list")
    print("  List cron jobs:  uv run openclaw cron list")
    print("  View logs:       uv run openclaw logs tail")
    
    # Check if BOOTSTRAP.md exists
    ws_dir = workspace_dir or (Path.home() / ".openclaw" / "workspace")
    bootstrap_path = ws_dir / "BOOTSTRAP.md"
    if bootstrap_path.exists():
        print("\n🎯 First-time Setup:")
        print("  When you first chat with your agent, it will guide you through:")
        print("  - Choosing the agent's name and personality")
        print("  - Refining your preferences")
        print("  - Setting up any additional details")
        print("\n  This is a one-time conversation to help the agent learn about you.")
    
    print("\n⚡ Tips:")
    print("  - Install globally to avoid typing 'uv run':")
    print("    $ uv pip install -e .")
    print("  - Enable shell completion:")
    print("    $ uv run openclaw completion --install")
    print("  - Run in foreground to see logs:")
    print("    $ uv run openclaw start")
    
    print("\n🔒 Security:")
    print("  Run security audit: uv run openclaw security audit")
    print("  Docs: https://docs.openclaw.ai/security")
    
    print("\n" + "=" * 80 + "\n")
    
    logger.info("Onboarding wizard complete")
    
    return {
        "completed": True,
        "skipped": False,
        "mode": mode,
        "provider": provider_config.get("provider") if provider_config else None,
    }


def _confirm_risks() -> bool:
    """Confirm user understands risks"""
    print("\n" + "-" * 80)
    print("⚠️  Important: Security & Risks")
    print("-" * 80)
    print("""
OpenClaw is an AI agent that can:
  • Execute commands on your system
  • Read and modify files
  • Make network requests
  • Use your API keys

Please ensure:
  ✓ You trust the codebase
  ✓ You understand the permissions granted
  ✓ You review agent actions carefully
  ✓ You keep your API keys secure

This is experimental software. Use at your own risk.
""")
    
    confirm = input("Do you understand and accept these risks? [y/N]: ").strip().lower()
    return confirm == "y"


def _select_mode() -> str:
    """Select onboarding mode"""
    print("\n" + "-" * 80)
    print("Onboarding Mode")
    print("-" * 80)
    print("\nChoose your setup mode:")
    print("  1. QuickStart  - Fast setup with recommended settings (5 min)")
    print("  2. Advanced    - Customize everything (15 min)")
    
    choice = input("\nSelect mode [1]: ").strip()
    
    if choice == "2":
        print("\n✓ Advanced mode selected")
        return "advanced"
    else:
        print("\n✓ QuickStart mode selected")
        return "quickstart"


def _prompt_config_action() -> str:
    """Prompt for action on existing config"""
    print("\nWhat would you like to do with existing configuration?")
    print("  1. Keep    - Use existing configuration")
    print("  2. Modify  - Update specific settings")
    print("  3. Reset   - Start fresh")
    
    choice = input("\nSelect action [2]: ").strip()
    
    if choice == "1":
        return "keep"
    elif choice == "3":
        return "reset"
    else:
        return "modify"


async def _configure_provider(mode: str) -> Optional[dict]:
    """Configure LLM provider"""
    print("\n" + "-" * 80)
    print("Provider Configuration")
    print("-" * 80)
    
    if mode == "quickstart":
        # QuickStart: Check environment variables first
        providers = ["anthropic", "openai", "gemini"]
        for provider in providers:
            if check_env_api_key(provider):
                print(f"\n✓ Found {provider.title()} API key in environment")
                use_it = input(f"Use {provider.title()}? [Y/n]: ").strip().lower()
                if use_it != "n":
                    return {
                        "provider": provider,
                        "model": "claude-sonnet-4" if provider == "anthropic" else f"{provider}-default",
                    }
    
    # Prompt for provider
    print("\nSelect your LLM provider:")
    print("  1. Anthropic (Claude)  - Recommended")
    print("  2. OpenAI (GPT-4)")
    print("  3. Google (Gemini)")
    print("  4. Ollama (Local)")
    
    choice = input("\nSelect provider [1]: ").strip()
    
    provider_map = {
        "1": "anthropic",
        "2": "openai",
        "3": "gemini",
        "4": "ollama",
    }
    provider = provider_map.get(choice, "anthropic")
    
    # Configure auth (skips if Ollama)
    if provider != "ollama":
        try:
            auth_result = configure_auth(provider)
            print(f"\n✓ {provider.title()} configured")
        except Exception as e:
            print(f"\n✗ Failed to configure {provider}: {e}")
            return None
    
    # Select model
    model_map = {
        "anthropic": "claude-sonnet-4",
        "openai": "gpt-4",
        "gemini": "gemini-pro",
        "ollama": "llama2",
    }
    model = model_map.get(provider, "claude-sonnet-4")
    
    return {"provider": provider, "model": model}


async def _configure_agent_settings() -> Optional[dict]:
    """Configure agent settings"""
    print("\n" + "-" * 80)
    print("Agent Settings")
    print("-" * 80)
    
    return await configure_agent()


async def _configure_gateway(mode: str) -> Optional[dict]:
    """Configure Gateway settings"""
    print("\n" + "-" * 80)
    print("Gateway Configuration")
    print("-" * 80)
    
    config = {}
    
    # Port
    if mode == "quickstart":
        config["port"] = 18789
        print(f"\nUsing default port: {config['port']}")
    else:
        port_input = input("\nGateway port [18789]: ").strip()
        config["port"] = int(port_input) if port_input else 18789
    
    # Bind mode
    if mode == "quickstart":
        config["bind"] = "loopback"
        print("Using loopback mode (local access only)")
    else:
        print("\nBind mode:")
        print("  1. loopback  - Local access only (recommended)")
        print("  2. lan       - LAN access")
        print("  3. auto      - Auto-detect")
        
        bind_choice = input("\nSelect bind mode [1]: ").strip()
        bind_map = {"1": "loopback", "2": "lan", "3": "auto"}
        config["bind"] = bind_map.get(bind_choice, "loopback")
    
    # Authentication
    if mode == "quickstart":
        # Generate token
        config["auth_token"] = secrets.token_urlsafe(32)
        print("\n✓ Generated authentication token")
    else:
        print("\nAuthentication:")
        print("  1. Token     - Random token (recommended)")
        print("  2. Password  - Custom password")
        print("  3. None      - No authentication (local only)")
        
        auth_choice = input("\nSelect auth mode [1]: ").strip()
        
        if auth_choice == "2":
            password = input("Enter password: ").strip()
            if password:
                config["auth_password"] = password
        elif auth_choice == "3":
            print("⚠️  Warning: No authentication - use only for local development")
        else:
            config["auth_token"] = secrets.token_urlsafe(32)
            print("✓ Generated authentication token")
    
    return config


async def _configure_channels(mode: str) -> Optional[dict]:
    """Configure channels"""
    print("\n" + "-" * 80)
    print("Channels Configuration")
    print("-" * 80)
    
    if mode == "quickstart":
        setup_channels = input("\nConfigure channels now? [y/N]: ").strip().lower()
        if setup_channels != "y":
            print("Skipping channels. You can configure them later with:")
            print("  $ openclaw configure channels")
            return None
    
    channels_config = {}
    
    print("\nWhich channels would you like to configure?")
    print("  1. Telegram")
    print("  2. Discord")
    print("  3. Skip")
    
    choice = input("\nSelect channel [3]: ").strip()
    
    if choice == "1":
        print("\n" + "~" * 60)
        print("Configuring Telegram")
        print("~" * 60)
        telegram_config = configure_telegram_enhanced()
        if telegram_config:
            channels_config["telegram"] = telegram_config
    elif choice == "2":
        print("\n" + "~" * 60)
        print("Configuring Discord")
        print("~" * 60)
        discord_config = configure_discord_enhanced()
        if discord_config:
            channels_config["discord"] = discord_config
    
    return channels_config if channels_config else None


def mark_onboarding_complete(workspace_dir: Path) -> None:
    """Mark onboarding as complete"""
    marker_file = workspace_dir / ".openclaw" / "onboarding-complete"
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    
    marker_data = {
        "completed_at": datetime.now().isoformat(),
        "version": "0.6.0",
    }
    
    marker_file.write_text(json.dumps(marker_data, indent=2))
    logger.info(f"Onboarding marked complete: {marker_file}")


def is_first_run(workspace_dir: Path) -> bool:
    """
    Check if this is the first run
    
    Args:
        workspace_dir: Workspace directory
        
    Returns:
        True if first run
    """
    marker_file = workspace_dir / ".openclaw" / "onboarding-complete"
    return not marker_file.exists()
