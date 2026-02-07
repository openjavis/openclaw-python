"""
Example 10: Gateway + Telegram Bridge (Full Architecture)

This example demonstrates the complete OpenClaw architecture matching
the TypeScript implementation:

Architecture:
    ┌──────────────────────────────────────────────────────┐
    │            Gateway Server                            │
    │                                                      │
    │  ┌────────────────────────────────────────────────┐ │
    │  │         ChannelManager                         │ │
    │  │  (manages channel plugins)                     │ │
    │  │                                                │ │
    │  │  ┌──────────────┐  ┌──────────────┐          │ │
    │  │  │  Telegram    │  │   Discord    │  ...     │ │
    │  │  │  (Plugin)    │  │   (Plugin)   │          │ │
    │  │  └──────┬───────┘  └──────────────┘          │ │
    │  │         │                                      │ │
    │  │         │ HTTP Polling                         │ │
    │  │         ↓                                      │ │
    │  │    Telegram API                                │ │
    │  └────────────────────────────────────────────────┘ │
    │                                                      │
    │  ┌────────────────────────────────────────────────┐ │
    │  │      WebSocket Server (ws://localhost:8765)   │ │
    │  │      (for external clients: UI, CLI, mobile)  │ │
    │  └────────────────────────────────────────────────┘ │
    │                                                      │
    │  ┌────────────────────────────────────────────────┐ │
    │  │      Event Broadcasting (Observer Pattern)    │ │
    │  │      (receives events from Agent Runtime)     │ │
    │  └────────────────────────────────────────────────┘ │
    │                        ↑                             │
    │                        │ events                      │
    │  ┌─────────────────────┴──────────────────────────┐ │
    │  │              Agent Runtime                     │ │
    │  │  • Process messages                           │ │
    │  │  • Call LLM APIs                              │ │
    │  │  • Emit events (observed by Gateway)          │ │
    │  └────────────────────────────────────────────────┘ │
    └──────────────────────────────────────────────────────┘

Key Points:
- Channels are INSIDE Gateway (managed by ChannelManager)
- Channels call Agent Runtime via function calls (not HTTP/WebSocket)
- Gateway observes Agent Runtime events (Observer Pattern)
- WebSocket is for EXTERNAL clients only (UI, CLI, mobile)

Prerequisites:
1. Create .env file with:
   - TELEGRAM_BOT_TOKEN=your_telegram_token
   - LLM_MODEL=anthropic/claude-3-5-sonnet (optional)
   - ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY (depends on your model)


2. Environment variables are loaded automatically from .env file

3. Supported models:
   - anthropic/claude-3-5-sonnet (requires ANTHROPIC_API_KEY)
   - anthropic/claude-opus (requires ANTHROPIC_API_KEY)
   - openai/gpt-4 (requires OPENAI_API_KEY)
   - openai/gpt-4-turbo (requires OPENAI_API_KEY)
   - google/gemini-2.5-flash (requires GOOGLE_API_KEY)

Usage:
    # Start the integrated server
    uv run python examples/10_gateway_telegram_bridge.py

    # Then connect external client (optional)
    # wscat -c ws://localhost:8765
"""

import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file
# It might be not neccessary in macOS. However, in Windows it is useful.
import os
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import SessionManager
from openclaw.agents.tools.registry import get_tool_registry
from openclaw.channels.enhanced_telegram import EnhancedTelegramChannel
from openclaw.config import ClawdbotConfig
from openclaw.gateway import ChannelManager, GatewayServer
from openclaw.monitoring import setup_logging

logger = logging.getLogger(__name__)


def get_api_key_for_model(model: str) -> tuple[str | None, str]:
    """
    Extract API key from environment based on model provider.

    Model format: "provider/model-name"
    Examples:
    - "anthropic/claude-3-5-sonnet" -> ANTHROPIC_API_KEY
    - "openai/gpt-4" -> OPENAI_API_KEY
    - "google/gemini-2.5-flash" -> GOOGLE_API_KEY

    Args:
        model: Model name with provider prefix

    Returns:
        Tuple of (api_key, provider_name). api_key can be None if not found.
    """
    # Extract provider from model string
    if "/" in model:
        provider = model.split("/")[0].lower()
    else:
        provider = "anthropic"  # Default provider

    # Map provider to environment variable
    provider_env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "aws": "AWS_ACCESS_KEY_ID",
        "bedrock": "AWS_ACCESS_KEY_ID",
        "vectorengine": "OPENAI_API_KEY",  # VectorEngine uses OpenAI-compatible API key
    }

    env_var = provider_env_map.get(provider)
    if not env_var:
        return None, provider

    api_key = os.getenv(env_var)
    return api_key, provider


class OpenClawServer:
    """
    Complete OpenClaw Server implementation

    This matches the TypeScript OpenClaw architecture:
    - Gateway Server contains ChannelManager
    - ChannelManager manages all channel plugins
    - Channels call Agent Runtime directly (function calls)
    - Gateway observes Agent Runtime for event broadcasting

    Features:
    - ✅ ChannelManager with lifecycle management
    - ✅ Multiple channel support (Telegram, Discord, etc.)
    - ✅ Per-channel configuration (RuntimeEnv)
    - ✅ Observer Pattern for event broadcasting
    - ✅ WebSocket API for external clients
    """

    def __init__(self, config: ClawdbotConfig):
        self.config = config
        self.running = False

        # =====================================================================
        # 1. Core Components
        # =====================================================================

        # Workspace for session storage
        workspace = Path("./workspace")
        workspace.mkdir(exist_ok=True)

        # Session Manager
        self.session_manager = SessionManager(workspace)

        # Tool Registry
        self.tool_registry = get_tool_registry(self.session_manager)
        self.tools = self.tool_registry.get_tools_by_profile("messaging")
        logger.info(f"✅ Loaded {len(self.tools)} raw tool objects.")

        # Agent Runtime (shared by all channels)
        self.agent_runtime = AgentRuntime(
            model=config.agent.model,
            api_key=config.agent.api_key,
            enable_context_management=True,
            max_retries=3,
        )

        # =====================================================================
        # 2. Gateway Server (contains ChannelManager)
        # =====================================================================

        self.gateway = GatewayServer(
            config=config,
            agent_runtime=self.agent_runtime,
            session_manager=self.session_manager,
            auto_discover_channels=False,  # We'll register manually
        )

        # Access ChannelManager via Gateway
        self.channel_manager: ChannelManager = self.gateway.channel_manager

        logger.info("OpenClawServer initialized")

    def setup_channels(self) -> None:
        """
        Register and configure channel plugins

        This is where you register all your channels with ChannelManager.
        Channels are plugins managed by Gateway.
        """
        # =====================================================================
        # Register Telegram Channel
        # =====================================================================

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            # Register channel class with ChannelManager
            self.channel_manager.register(
                channel_id="telegram",
                channel_class=EnhancedTelegramChannel,
                config={
                    "bot_token": bot_token,
                    "parse_mode": "Markdown",
                },
                runtime=self.agent_runtime,
            )
            env = self.channel_manager.get_runtime_env("telegram")
            if env:
                env.tools = self.tools
                logger.info("🛠️ Tools attached to Telegram runtime environment")
            logger.info("✅ Telegram channel registered")
        else:
            logger.warning("⚠️ TELEGRAM_BOT_TOKEN not set, Telegram disabled")

        # =====================================================================
        # Register Discord Channel (example, disabled by default)
        # =====================================================================

        discord_token = os.getenv("DISCORD_BOT_TOKEN")
        if discord_token:
            from openclaw.channels.enhanced_discord import EnhancedDiscordChannel

            self.channel_manager.register(
                channel_id="discord",
                channel_class=EnhancedDiscordChannel,
                config={
                    "bot_token": discord_token,
                },
            )
            logger.info("✅ Discord channel registered")

        # =====================================================================
        # You can also set custom runtime per channel
        # =====================================================================

        # Example: Use different model for a specific channel
        # custom_runtime = AgentRuntime(model="anthropic/claude-haiku")
        # self.channel_manager.set_runtime("telegram", custom_runtime)

        logger.info(f"Registered {len(self.channel_manager.list_channels())} channels")

    async def start(self) -> None:
        """
        Start the OpenClaw server

        This starts:
        1. Gateway WebSocket server
        2. All enabled channel plugins via ChannelManager
        """
        logger.info("🚀 Starting OpenClaw Server...")

        # Setup channels
        self.setup_channels()
        self.running = True

        gateway_task = asyncio.create_task(self.gateway.start(start_channels=True))

        await asyncio.sleep(0.1)  # Allow some time for startup

        # [NEW] Link channels to AgentRuntime events
        linked_count = 0
        for channel_id in self.channel_manager.list_channels():
            channel = self.channel_manager.get_channel(channel_id)
            if channel and hasattr(channel, "on_event"):
                self.agent_runtime.add_event_listener(channel.on_event)
                logger.info(f"🔗 [Circuit Link] Successfully linked {channel_id} to Agent events")
                linked_count += 1

        if linked_count == 0:
            logger.error("❌ Circuit Link Failed: No active channels found to link!")

        await gateway_task

        # Print status
        print()
        print("=" * 60)
        print("🦞 OpenClaw Python Server")
        print("=" * 60)
        print()
        print("Architecture:")
        print("  ┌─────────────────────────────────────────┐")
        print("  │           Gateway Server                │")
        print("  │                                         │")
        print("  │  ChannelManager                        │")
        for ch_id in self.channel_manager.list_channels():
            print(f"  │    └─ {ch_id.capitalize()} Channel (plugin)       │")
        print("  │                                         │")
        print("  │  WebSocket: ws://localhost:8765        │")
        print("  │                                         │")
        print("  │  Event Broadcasting (Observer Pattern) │")
        print("  │           ↑                             │")
        print("  │  ┌────────┴─────────────────────────┐  │")
        print("  │  │     Agent Runtime                │  │")
        print("  │  └──────────────────────────────────┘  │")
        print("  └─────────────────────────────────────────┘")
        print()
        print("=" * 60)
        print()

    async def stop(self) -> None:
        """Stop the OpenClaw server"""
        logger.info("⏹️ Stopping OpenClaw Server...")

        # Gateway.stop() also stops all channels via ChannelManager
        await self.gateway.stop()

        self.running = False
        logger.info("✅ Server stopped")


async def main():
    """Run OpenClaw server with full architecture"""

    # Setup logging
    setup_logging(level="INFO", format_type="colored")

    print()
    print("🦞 OpenClaw Python - Full Architecture Demo")
    print("=" * 60)
    print()
    print("This example demonstrates the complete TypeScript-matching")
    print("architecture with ChannelManager inside Gateway.")
    print()

    # Check requirements
    # Model is required, will try to extract API key from environment
    llm_model = os.getenv("LLM_MODEL")
    if not llm_model:
        print("❌ Error: LLM_MODEL not set!")
        print("   Add to .env file:")
        print("   LLM_MODEL=anthropic/claude-3-5-sonnet")
        print()
        print("   Supported models:")
        print("   - anthropic/claude-3-5-sonnet (requires ANTHROPIC_API_KEY)")
        print("   - openai/gpt-4 (requires OPENAI_API_KEY)")
        print("   - google/gemini-2.5-flash (requires GOOGLE_API_KEY)")
        return

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("⚠️ Warning: TELEGRAM_BOT_TOKEN not set")
        print("   Gateway will start but Telegram channel will be disabled")
        print()

    # Intelligently extract API key based on model provider
    api_key, provider = get_api_key_for_model(llm_model)

    if not api_key:
        print(f"❌ Error: API key not found for provider '{provider}'!")
        print(f"   Expected environment variable: {provider.upper()}_API_KEY")
        print("   Add to .env file:")
        env_var = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
        }.get(provider, f"{provider.upper()}_API_KEY")
        print(f"   {env_var}=your_api_key_here")
        print()
        print("   Your .env should have:")
        print(f"   LLM_MODEL={llm_model}")
        print(f"   {env_var}=<your_key>")
        return

    config = ClawdbotConfig(
        gateway={
            "port": 8765,
            "bind": "loopback",
        },
        agent={
            "model": llm_model,
            "api_key": api_key,
        },
    )

    # Create and start server
    server = OpenClawServer(config)

    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
