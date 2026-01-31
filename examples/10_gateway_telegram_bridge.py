"""
Example 10: Gateway + Telegram Bridge

This example demonstrates how to connect Telegram Bot to Gateway Server,
similar to the TypeScript OpenClaw architecture.

Architecture:
    Telegram User → Telegram Bot API
                         ↓
                    Telegram Monitor (in same process)
                         ↓
                    Gateway Server (WebSocket)
                         ↓
                    Agent Runtime

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
from typing import Any

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import SessionManager
from openclaw.agents.tools.registry import ToolRegistry
from openclaw.channels.base import InboundMessage
from openclaw.channels.enhanced_telegram import EnhancedTelegramChannel
from openclaw.channels.registry import ChannelRegistry
from openclaw.config import ClawdbotConfig
from openclaw.gateway.server import GatewayServer
from openclaw.monitoring import setup_logging

logger = logging.getLogger(__name__)


class IntegratedOpenClawServer:
    """
    Integrated OpenClaw Server that runs:
    - Gateway Server (WebSocket)
    - Telegram Bot (as a channel plugin)
    - Agent Runtime
    
    This mirrors the TypeScript OpenClaw architecture where
    channels and gateway run in the same process.
    """
    
    def __init__(self, config: ClawdbotConfig):
        self.config = config
        self.running = False
        
        # Core components
        workspace = Path("./workspace")
        workspace.mkdir(exist_ok=True)
        
        self.session_manager = SessionManager(workspace)
        self.tool_registry = ToolRegistry()
        self.agent_runtime = AgentRuntime(
            model="anthropic/claude-opus-4",
            enable_context_management=True,
            max_retries=3
        )
        
        # Channel registry
        self.channel_registry = ChannelRegistry()
        
        # Gateway server (register as observer of agent_runtime)
        self.gateway_server = GatewayServer(config, self.agent_runtime)
        
        # Telegram channel (optional)
        self.telegram_channel: EnhancedTelegramChannel | None = None
        
    async def setup_telegram(self, bot_token: str) -> None:
        """Setup Telegram channel as a server-side plugin"""
        logger.info("Setting up Telegram channel plugin...")
        
        self.telegram_channel = EnhancedTelegramChannel()
        
        # Set message handler that processes through agent
        async def handle_telegram_message(message: InboundMessage):
            """Handle Telegram message through agent runtime"""
            logger.info(f"📨 Telegram message from {message.sender_name}: {message.text}")
            
            # Get session for this chat
            session_id = f"telegram-{message.chat_id}"
            session = self.session_manager.get_session(session_id)
            
            try:
                # Process through agent
                response_text = ""
                async for event in self.agent_runtime.run_turn(session, message.text):
                    if event.type == "assistant":
                        delta = event.data.get("delta", {})
                        if "text" in delta:
                            response_text += delta["text"]
                
                # Send response back to Telegram
                if response_text:
                    await self.telegram_channel.send_text(
                        message.chat_id,
                        response_text,
                        reply_to=message.message_id
                    )
                    logger.info(f"✅ Sent response to Telegram ({len(response_text)} chars)")
                    
                    # ✅ No need to call gateway.broadcast_event()
                    # Gateway automatically receives events via observer pattern
                    
            except Exception as e:
                logger.error(f"❌ Error processing Telegram message: {e}", exc_info=True)
                if self.telegram_channel:
                    await self.telegram_channel.send_text(
                        message.chat_id,
                        f"Sorry, I encountered an error: {e}",
                        reply_to=message.message_id
                    )
        
        self.telegram_channel.set_message_handler(handle_telegram_message)
        
        # Register channel
        self.channel_registry.register(self.telegram_channel)
        
        # Start Telegram bot
        await self.telegram_channel.start({"bot_token": bot_token})
        logger.info("✅ Telegram channel plugin registered and started")
        
    async def start(self) -> None:
        """Start the integrated server"""
        logger.info("🚀 Starting OpenClaw Integrated Server...")
        
        # Setup Telegram if token available
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            await self.setup_telegram(bot_token)
        else:
            logger.warning("⚠️  TELEGRAM_BOT_TOKEN not set, Telegram channel disabled")
        
        # Start Gateway server
        logger.info("🌐 Starting Gateway server...")
        gateway_task = asyncio.create_task(self.gateway_server.start())
        
        self.running = True
        logger.info("✅ Server started successfully!")
        logger.info("")
        logger.info("=" * 60)
        logger.info("📡 Gateway WebSocket: ws://localhost:8765")
        if self.telegram_channel:
            logger.info("📱 Telegram Bot: Send messages to your bot")
        logger.info("=" * 60)
        logger.info("")
        
        # Wait for server to complete
        await gateway_task
        
    async def stop(self) -> None:
        """Stop the integrated server"""
        logger.info("⏹️  Stopping server...")
        
        # Stop Telegram channel
        if self.telegram_channel:
            await self.telegram_channel.stop()
            logger.info("✅ Telegram channel stopped")
        
        # Stop Gateway server
        await self.gateway_server.stop()
        logger.info("✅ Gateway server stopped")
        
        self.running = False


async def main():
    """Run integrated OpenClaw server"""
    
    # Setup logging
    setup_logging(level="INFO", format_type="colored")
    
    print("🦞 OpenClaw Python - Integrated Server")
    print("=" * 60)
    print()
    print("Architecture:")
    print("  Telegram User → Telegram Bot (plugin)")
    print("                       ↓")
    print("                  Gateway Server")
    print("                       ↓")
    print("                  Agent Runtime")
    print()
    print("=" * 60)
    print()
    
    # Check requirements
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    has_llm_key = any([
        os.getenv("ANTHROPIC_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("GOOGLE_API_KEY"),
    ])
    
    if not has_llm_key:
        print("❌ Error: No LLM API key found!")
        print("   Set one of: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY")
        return
    
    if not bot_token:
        print("⚠️  Warning: TELEGRAM_BOT_TOKEN not set")
        print("   Gateway will start but Telegram channel will be disabled")
        print()
    
    # Create config
    config = ClawdbotConfig(
        gateway={
            "port": 8765,
            "bind": "loopback",
        },
        agent={
            "model": "anthropic/claude-opus-4",
            "max_tokens": 2000,
        }
    )
    
    # Create and start server
    server = IntegratedOpenClawServer(config)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n")
        await server.stop()
        print("✅ Server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
