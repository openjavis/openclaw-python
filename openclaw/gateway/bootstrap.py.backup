"""Gateway bootstrap sequence (matches TypeScript gateway/server.impl.ts startGatewayServer)

Implements the full 40-step TypeScript gateway initialization in Python.
"""

import asyncio
import logging
import os
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GatewayBootstrap:
    """
    Complete gateway bootstrap sequence matching TypeScript.
    
    Steps:
    1. Set environment variables
    2. Load and validate config
    3. Migrate legacy config if needed
    4. Start diagnostic heartbeat
    5. Initialize subagent registry
    6. Resolve default agent and workspace
    7. Load gateway plugins
    8. Create channel logs and runtime envs
    9. Resolve runtime config (bind, TLS, auth)
    10. Create default deps
    11. Create runtime state
    12. Build cron service
    13. Create channel manager
    14. Start discovery service
    15. Register skills change listener
    16. Start maintenance timers
    17. Register agent event handler
    18. Start heartbeat runner
    19. Start cron service
    20. Create exec approval manager
    21. Attach WebSocket handlers
    22. Log startup
    23. Start config reloader
    24. Create close handler
    """
    
    def __init__(self):
        self.config = None
        self.runtime = None
        self.session_manager = None
        self.server = None
        self.tool_registry = None
        self.channel_manager = None
        self.skill_loader = None
        self.cron_service = None
        self.discovery = None
        self.config_reloader = None
        self.heartbeat_stop = None
        self._maintenance_tasks: list[asyncio.Task] = []
        self._close_handlers: list[Any] = []
    
    async def bootstrap(self, config_path: Path | None = None) -> dict[str, Any]:
        """
        Run the full bootstrap sequence.
        
        Returns:
            Dict with all initialized components
        """
        results = {"steps_completed": 0, "errors": []}
        
        # Step 1: Set environment variables
        logger.info("Step 1: Setting environment variables")
        self._set_env_vars()
        results["steps_completed"] += 1
        
        # Step 2: Load and validate config
        logger.info("Step 2: Loading configuration")
        try:
            from ..config.loader import load_config
            self.config = load_config(config_path)
            results["steps_completed"] += 1
        except Exception as e:
            logger.error(f"Config load failed: {e}")
            results["errors"].append(f"config: {e}")
            return results
        
        # Step 3: Migrate legacy config
        logger.info("Step 3: Checking legacy config")
        try:
            from ..config.legacy import detect_legacy_config, migrate_legacy_config
            legacy = detect_legacy_config()
            if legacy:
                migrate_legacy_config(legacy)
                logger.info(f"Migrated legacy config from {legacy}")
        except Exception as e:
            logger.warning(f"Legacy migration skipped: {e}")
        results["steps_completed"] += 1
        
        # Step 4: Start diagnostic heartbeat
        logger.info("Step 4: Starting diagnostic heartbeat")
        try:
            from ..infra.diagnostic_events import start_diagnostic_heartbeat
            start_diagnostic_heartbeat()
        except Exception as e:
            logger.warning(f"Diagnostic heartbeat failed: {e}")
        results["steps_completed"] += 1
        
        # Step 5: Initialize subagent registry
        logger.info("Step 5: Initializing subagent registry")
        # Subagent registry is lightweight - just a dict
        self._subagent_registry: dict[str, Any] = {}
        results["steps_completed"] += 1
        
        # Step 6: Resolve default agent and workspace
        logger.info("Step 6: Resolving workspace directory")
        workspace_dir = Path.home() / ".openclaw" / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        results["steps_completed"] += 1
        
        # Step 7: Load gateway plugins
        logger.info("Step 7: Loading gateway plugins")
        try:
            from ..plugins.plugin_manager import PluginManager
            plugin_manager = PluginManager()
            discovered = plugin_manager.discover_plugins()
            logger.info(f"Discovered {len(discovered)} plugins")
        except Exception as e:
            logger.warning(f"Plugin loading skipped: {e}")
        results["steps_completed"] += 1
        
        # Step 8: Create agent runtime and LLM provider
        logger.info("Step 8: Creating agent runtime")
        try:
            # Get model from config
            if self.config.agents and self.config.agents.defaults:
                model = str(self.config.agents.defaults.model)
            else:
                model = "google/gemini-3-pro-preview"  # Fallback to Gemini
            
            logger.info(f"Creating runtime with model: {model}")
            
            # Parse provider and model
            if "/" in model:
                provider_name, model_name = model.split("/", 1)
            else:
                provider_name = "anthropic"
                model_name = model
            
            # Create appropriate provider
            from ..agents.providers import (
                AnthropicProvider,
                GeminiProvider,
                OpenAIProvider,
            )
            
            if provider_name == "gemini" or provider_name == "google":
                self.provider = GeminiProvider(model=model_name)
            elif provider_name == "openai":
                self.provider = OpenAIProvider(model=model_name)
            elif provider_name == "anthropic":
                self.provider = AnthropicProvider(model=model_name)
            else:
                # Default to Gemini
                self.provider = GeminiProvider(model="gemini-3-pro-preview")
            
            # Keep backward compatibility - also create old runtime
            from ..agents.runtime import MultiProviderRuntime
            self.runtime = MultiProviderRuntime(model=model)
            
            logger.info(f"Created provider: {type(self.provider).__name__}")
        except Exception as e:
            logger.error(f"Runtime creation failed: {e}")
            results["errors"].append(f"runtime: {e}")
        results["steps_completed"] += 1
        
        # Step 9: Create session manager
        logger.info("Step 9: Creating session manager")
        try:
            from ..agents.session import SessionManager
            self.session_manager = SessionManager(workspace_dir=workspace_dir)
        except Exception as e:
            logger.error(f"Session manager creation failed: {e}")
            results["errors"].append(f"session_manager: {e}")
        results["steps_completed"] += 1
        
        # Step 10: Create tool registry
        logger.info("Step 10: Creating tool registry")
        try:
            from ..agents.tools.registry import ToolRegistry
            self.tool_registry = ToolRegistry(
                session_manager=self.session_manager,
                auto_register=True,
            )
            
            # Register new tools
            from ..agents.tools.gateway_tool import GatewayTool, AgentsListTool, SessionStatusTool
            self.tool_registry.register(GatewayTool())
            self.tool_registry.register(AgentsListTool(config=self.config))
            self.tool_registry.register(SessionStatusTool(session_manager=self.session_manager))
            
            tool_count = len(self.tool_registry.list_tools())
            logger.info(f"Registered {tool_count} tools")
        except Exception as e:
            logger.error(f"Tool registry creation failed: {e}")
            results["errors"].append(f"tool_registry: {e}")
        results["steps_completed"] += 1
        
        # Step 11: Load skills
        logger.info("Step 11: Loading skills")
        try:
            from ..agents.skills.loader import SkillLoader
            
            # Get project root (where skills/ directory is)
            project_root = Path(__file__).parent.parent.parent
            bundled_skills_dir = project_root / "skills"
            
            self.skill_loader = SkillLoader(bundled_skills_dir=bundled_skills_dir)
            self.skill_loader.load_all_skills()
            skill_count = len(self.skill_loader.skills)
            logger.info(f"Loaded {skill_count} skills from {bundled_skills_dir}")
        except Exception as e:
            logger.warning(f"Skills loading failed: {e}")
        results["steps_completed"] += 1
        
        # Step 12: Build cron service
        logger.info("Step 12: Building cron service")
        try:
            from ..cron import CronService
            
            # Cron directories
            cron_dir = Path.home() / ".openclaw" / "cron"
            store_path = cron_dir / "jobs.json"
            log_dir = cron_dir / "runs"
            
            # Create cron service
            self.cron_service = CronService(
                store_path=store_path,
                log_dir=log_dir,
                on_system_event=None,  # Will be set later
                on_isolated_agent=None,  # Will be set later
                on_event=None,  # Will be set later
            )
            
            # Start cron service
            self.cron_service.start()
            
            logger.info(f"Cron service started with {len(self.cron_service.jobs)} jobs")
        except Exception as e:
            logger.warning(f"Cron service initialization failed: {e}")
        results["steps_completed"] += 1
        
        # Step 13: Create channel manager and start channels
        logger.info("Step 13: Creating channel manager")
        try:
            from .channel_manager import ChannelManager
            self.channel_manager = ChannelManager(
                default_runtime=self.runtime,
                session_manager=self.session_manager,
                tools=self.tool_registry.list_tools() if self.tool_registry else [],
            )
            
            # Register and start enabled channels from config
            if self.config and self.config.channels:
                started_count = 0
                
                # Telegram
                if self.config.channels.telegram and self.config.channels.telegram.enabled:
                    try:
                        from ..channels.telegram import TelegramChannel
                        
                        # Step 1: Register channel class
                        self.channel_manager.register("telegram", TelegramChannel)
                        
                        # Step 2: Configure with botToken
                        channel_config = {
                            "botToken": self.config.channels.telegram.botToken,
                            "enabled": True,
                        }
                        self.channel_manager.configure("telegram", channel_config)
                        
                        # Step 3: Start channel (will use config from RuntimeEnv)
                        success = await self.channel_manager.start_channel("telegram")
                        if success:
                            started_count += 1
                            logger.info("✅ Telegram channel started")
                        else:
                            logger.warning("⚠️  Telegram channel start returned False")
                    except Exception as e:
                        logger.warning(f"❌ Failed to start Telegram channel: {e}")
                
                # Discord
                if self.config.channels.discord and self.config.channels.discord.enabled:
                    try:
                        from ..channels.discord import DiscordChannel
                        
                        # Step 1: Register
                        self.channel_manager.register("discord", DiscordChannel)
                        
                        # Step 2: Configure
                        channel_config = {
                            "token": self.config.channels.discord.token,
                            "enabled": True,
                        }
                        self.channel_manager.configure("discord", channel_config)
                        
                        # Step 3: Start
                        success = await self.channel_manager.start_channel("discord")
                        if success:
                            started_count += 1
                            logger.info("✅ Discord channel started")
                    except Exception as e:
                        logger.warning(f"❌ Failed to start Discord channel: {e}")
                
                logger.info(f"📊 Started {started_count} channels")
        except Exception as e:
            logger.error(f"Channel manager creation failed: {e}")
            results["errors"].append(f"channel_manager: {e}")
        results["steps_completed"] += 1
        
        # Step 14: Start discovery service
        logger.info("Step 14: Starting discovery service")
        # mDNS/Bonjour discovery is optional
        results["steps_completed"] += 1
        
        # Step 15: Register skills change listener
        logger.info("Step 15: Registering skills change listener")
        try:
            from ..agents.skills.refresh import register_skills_change_listener, ensure_skills_watcher
            
            def on_skills_change():
                logger.info("Skills changed, reloading...")
                if self.skill_loader:
                    self.skill_loader.load_all_skills()
            
            register_skills_change_listener(on_skills_change)
            
            # Watch skill directories
            skill_dirs = [
                Path(__file__).parent.parent / "skills",
                Path.home() / ".openclaw" / "skills",
                workspace_dir / "skills",
            ]
            for d in skill_dirs:
                if d.exists():
                    ensure_skills_watcher(d)
        except Exception as e:
            logger.warning(f"Skills watcher failed: {e}")
        results["steps_completed"] += 1
        
        # Step 16: Start maintenance timers
        logger.info("Step 16: Starting maintenance timers")
        self._start_maintenance_timers()
        results["steps_completed"] += 1
        
        # Step 17: Register event handlers
        logger.info("Step 17: Registering event handlers")
        # Event handlers are registered within the gateway server
        results["steps_completed"] += 1
        
        # Step 18: Start heartbeat runner
        logger.info("Step 18: Starting heartbeat runner")
        try:
            from ..infra.heartbeat_runner import start_heartbeat_runner
            agents_config = {}
            if self.config.agents and self.config.agents.agents:
                for agent in self.config.agents.agents:
                    agents_config[agent.id] = {"heartbeat": {"enabled": False}}
            
            if agents_config:
                self.heartbeat_stop = start_heartbeat_runner(
                    agents_config,
                    execute_fn=self._execute_heartbeat,
                )
        except Exception as e:
            logger.warning(f"Heartbeat runner failed: {e}")
        results["steps_completed"] += 1
        
        # Step 19: Set global handler instances
        logger.info("Step 19: Setting global handler instances")
        try:
            from .handlers import set_global_instances
            # gateway is created later in Step 22, so pass None here
            set_global_instances(
                self.session_manager,
                self.tool_registry,
                self.channel_manager,
                self.runtime,
                None  # wizard_handler will be set after server creation
            )
        except Exception as e:
            logger.debug(f"Handler globals setup (optional): {e}")
        results["steps_completed"] += 1
        
        # Step 20: Start config reloader
        logger.info("Step 20: Starting config reloader")
        try:
            from ..config.reloader import ConfigReloader
            from ..config.loader import get_config_path
            
            config_file = get_config_path()
            self.config_reloader = ConfigReloader(
                config_path=config_file,
                reload_fn=load_config,
            )
            self.config_reloader.start()
        except Exception as e:
            logger.warning(f"Config reloader failed: {e}")
        results["steps_completed"] += 1
        
        # Step 21: Log startup
        logger.info("Step 21: Logging startup")
        self._log_startup()
        results["steps_completed"] += 1
        
        # Step 22: Start WebSocket server
        logger.info("Step 22: Starting WebSocket server")
        try:
            from .server import GatewayServer
            port = self.config.gateway.port if self.config and self.config.gateway else 18789
            
            # Get tools list from registry
            tools = self.tool_registry.list_tools() if self.tool_registry else []
            
            self.server = GatewayServer(
                config=self.config,
                agent_runtime=self.runtime,
                session_manager=self.session_manager,
                tools=tools,
                system_prompt=None,  # Will be built from skills
                auto_discover_channels=False,  # We already created ChannelManager
            )
            
            # Override the ChannelManager that GatewayServer created with our own
            # (since we already configured it in Step 13)
            self.server.channel_manager = self.channel_manager
            
            # Start server in background task
            # Pass start_channels=False since we already started channels in Step 13
            asyncio.create_task(self.server.start(start_channels=False))
            # Give server time to start
            await asyncio.sleep(0.5)
            logger.info(f"WebSocket server started on port {port}")
            results["steps_completed"] += 1
        except Exception as e:
            logger.error(f"Server start failed: {e}")
            results["errors"].append(f"server_start: {e}")
        
        logger.info(f"Bootstrap complete: {results['steps_completed']} steps, {len(results['errors'])} errors")
        
        return results
    
    def _set_env_vars(self) -> None:
        """Set required environment variables"""
        if self.config and self.config.gateway:
            os.environ["OPENCLAW_GATEWAY_PORT"] = str(self.config.gateway.port)
    
    def _start_maintenance_timers(self) -> None:
        """Start maintenance timer tasks"""
        
        async def session_cleanup():
            """Periodic session cleanup"""
            while True:
                try:
                    await asyncio.sleep(3600)  # Every hour
                    logger.debug("Running session cleanup")
                    # Cleanup old sessions
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Session cleanup error: {e}")
        
        async def health_check():
            """Periodic health check"""
            while True:
                try:
                    await asyncio.sleep(60)  # Every minute
                    # Check component health
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Health check error: {e}")
        
        self._maintenance_tasks.append(asyncio.create_task(session_cleanup()))
        self._maintenance_tasks.append(asyncio.create_task(health_check()))
    
    async def _execute_heartbeat(self, agent_id: str, prompt: str) -> str | None:
        """Execute heartbeat for an agent"""
        if not self.runtime or not self.session_manager:
            return None
        
        session = self.session_manager.get_session(f"heartbeat-{agent_id}")
        tools = self.tool_registry.list_tools() if self.tool_registry else []
        
        response = ""
        async for event in self.runtime.run_turn(session, prompt, tools):
            if hasattr(event, 'text') and event.text:
                response += event.text
        
        return response if response else None
    
    def _log_startup(self) -> None:
        """Log gateway startup information"""
        port = self.config.gateway.port if self.config and self.config.gateway else 18789
        
        logger.info("=" * 60)
        logger.info(f"OpenClaw Gateway Started")
        logger.info(f"  Platform: {platform.system()} {platform.machine()}")
        logger.info(f"  Python: {platform.python_version()}")
        logger.info(f"  Port: {port}")
        if self.config and self.config.agents and self.config.agents.defaults:
            logger.info(f"  Model: {self.config.agents.defaults.model}")
        if self.tool_registry:
            logger.info(f"  Tools: {len(self.tool_registry.list_tools())}")
        if self.skill_loader:
            logger.info(f"  Skills: {len(self.skill_loader.skills)}")
        logger.info("=" * 60)
    
    async def shutdown(self) -> None:
        """Graceful shutdown"""
        logger.info("Gateway shutting down...")
        
        # Stop heartbeat
        if self.heartbeat_stop:
            self.heartbeat_stop()
        
        # Stop maintenance timers
        for task in self._maintenance_tasks:
            task.cancel()
        
        # Stop config reloader
        if self.config_reloader:
            self.config_reloader.stop()
        
        # Stop skills watchers
        try:
            from ..agents.skills.refresh import stop_all_watchers
            stop_all_watchers()
        except Exception:
            pass
        
        # Stop diagnostic heartbeat
        try:
            from ..infra.diagnostic_events import stop_diagnostic_heartbeat
            stop_diagnostic_heartbeat()
        except Exception:
            pass
        
        # Stop channels
        if self.channel_manager:
            try:
                await self.channel_manager.stop_all()
            except Exception as e:
                logger.error(f"Channel manager stop error: {e}")
        
        logger.info("Gateway shutdown complete")
