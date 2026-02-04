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
1. Set TELEGRAM_BOT_TOKEN environment variable
2. Set LLM API key (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GOOGLE_API_KEY)

Usage:
    # Start the integrated server
    uv run python examples/10_gateway_telegram_bridge.py

    # Then connect external client (optional)
    # wscat -c ws://localhost:8765
"""

import asyncio
import logging
import os
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import SessionManager
from openclaw.channels.enhanced_telegram import EnhancedTelegramChannel
from openclaw.config import ClawdbotConfig
from openclaw.gateway import GatewayServer, ChannelManager
from openclaw.monitoring import setup_logging

logger = logging.getLogger(__name__)


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

        # Agent Runtime (shared by all channels)
        self.agent_runtime = AgentRuntime(
            model=config.agent.get("model", "gemini/gemini-3-flash-preview"),
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
            )
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

        # Start Gateway (this also starts all channels via ChannelManager)
        await self.gateway.start(start_channels=True)

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
    has_llm_key = any(
        [
            os.getenv("ANTHROPIC_API_KEY"),
            os.getenv("OPENAI_API_KEY"),
            os.getenv("GOOGLE_API_KEY"),
        ]
    )

    if not has_llm_key:
        print("❌ Error: No LLM API key found!")
        print("   Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY")
        return

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("⚠️ Warning: TELEGRAM_BOT_TOKEN not set")
        print("   Gateway will start but Telegram channel will be disabled")
        print()

    # Create config
    config = ClawdbotConfig(
        gateway={
            "port": 8765,
            "bind": "loopback",
        },
        agent={
            "model": "gemini/gemini-3-flash-preview",
            "max_tokens": 4000,
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
