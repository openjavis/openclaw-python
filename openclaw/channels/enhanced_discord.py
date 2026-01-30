"""
Enhanced Discord channel with connection management
"""

import asyncio
import logging
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin, InboundMessage
from .connection import ReconnectConfig

logger = logging.getLogger(__name__)


class EnhancedDiscordChannel(ChannelPlugin):
    """
    Enhanced Discord bot channel with:
    - Automatic reconnection
    - Health checking
    - Connection metrics
    - Better error handling
    """

    def __init__(self):
        super().__init__()
        self.id = "discord"
        self.label = "Discord"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group", "channel"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=True,
            supports_polls=False,
        )
        self._client: Any | None = None
        self._bot_token: str | None = None
        self._ready_event: asyncio.Event | None = None

        # Setup connection manager
        self._setup_connection_manager(
            reconnect_config=ReconnectConfig(
                enabled=True,
                max_attempts=10,
                base_delay=2.0,
                max_delay=300.0,
                exponential_backoff=True,
            )
        )

    async def start(self, config: dict[str, Any]) -> None:
        """Start Discord bot"""
        self._config = config
        self._bot_token = config.get("botToken") or config.get("bot_token")

        if not self._bot_token:
            raise ValueError("Discord bot token not provided")

        logger.info(f"[{self.id}] Starting Discord channel...")

        if self._connection_manager:
            success = await self._connection_manager.connect()
            if success:
                # Wait for bot to be ready
                if self._ready_event:
                    try:
                        await asyncio.wait_for(self._ready_event.wait(), timeout=30.0)
                    except TimeoutError:
                        logger.warning(f"[{self.id}] Timeout waiting for Discord ready")

                # Setup health checker
                self._setup_health_checker(interval=60.0, timeout=15.0)
                if self._health_checker:
                    self._health_checker.start()
        else:
            await self._do_connect()

    async def _do_connect(self) -> None:
        """Internal connection implementation"""
        try:
            import discord
            from discord.ext import commands
        except ImportError:
            raise ImportError("discord.py not installed. Install with: pip install discord.py")

        if self._client:
            await self._do_disconnect()

        self._ready_event = asyncio.Event()

        # Setup intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guilds = True

        # Create bot
        self._client = commands.Bot(command_prefix="!", intents=intents, help_command=None)

        # Register event handlers
        @self._client.event
        async def on_ready():
            logger.info(f"[{self.id}] Discord bot logged in as {self._client.user}")
            self._running = True
            if self._ready_event:
                self._ready_event.set()

        @self._client.event
        async def on_disconnect():
            logger.warning(f"[{self.id}] Discord disconnected")
            if self._connection_manager:
                self._connection_manager.handle_connection_error(Exception("Discord disconnected"))

        @self._client.event
        async def on_resumed():
            logger.info(f"[{self.id}] Discord connection resumed")

        @self._client.event
        async def on_error(event, *args, **kwargs):
            logger.error(f"[{self.id}] Discord error in {event}")
            if self._connection_manager:
                self._connection_manager.metrics.record_error(f"Error in {event}")

        @self._client.event
        async def on_message(message):
            if message.author == self._client.user:
                return
            if message.content.startswith("!"):
                return
            await self._handle_discord_message(message)

        # Start bot in background
        asyncio.create_task(self._run_client())

    async def _run_client(self) -> None:
        """Run Discord client with error handling"""
        try:
            await self._client.start(self._bot_token)
        except Exception as e:
            logger.error(f"[{self.id}] Discord client error: {e}")
            if self._connection_manager:
                self._connection_manager.handle_connection_error(e)

    async def _do_disconnect(self) -> None:
        """Internal disconnection implementation"""
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"[{self.id}] Error closing Discord client: {e}")
            finally:
                self._client = None

        self._running = False
        self._ready_event = None

    async def _health_check(self) -> bool:
        """Check if Discord connection is healthy"""
        if not self._client or not self._running:
            return False

        try:
            # Check if client is connected and ready
            return self._client.is_ready() and not self._client.is_closed()
        except Exception as e:
            logger.warning(f"[{self.id}] Health check failed: {e}")
            return False

    async def stop(self) -> None:
        """Stop Discord bot"""
        logger.info(f"[{self.id}] Stopping Discord channel...")

        if self._health_checker:
            self._health_checker.stop()

        if self._connection_manager:
            await self._connection_manager.disconnect()
        else:
            await self._do_disconnect()

        logger.info(f"[{self.id}] Discord channel stopped")

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message with retry"""
        if not self._client:
            raise RuntimeError("Discord channel not started")

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                channel_id = int(target)
                channel = self._client.get_channel(channel_id)

                if not channel:
                    # Try to fetch channel
                    channel = await self._client.fetch_channel(channel_id)

                if not channel:
                    raise ValueError(f"Channel not found: {channel_id}")

                # Get reference if replying
                reference = None
                if reply_to:
                    try:
                        ref_msg = await channel.fetch_message(int(reply_to))
                        reference = ref_msg.to_reference()
                    except Exception:
                        pass  # Ignore if can't find message

                message = await channel.send(text, reference=reference)
                await self._track_send()
                return str(message.id)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[{self.id}] Send failed (attempt {attempt + 1}/{max_retries}): {e}"
                )

                if self._connection_manager:
                    self._connection_manager.metrics.record_error(str(e))

                # Don't retry for certain errors
                error_str = str(e).lower()
                if any(x in error_str for x in ["forbidden", "not found", "invalid"]):
                    break

                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))

        raise last_error

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._client:
            raise RuntimeError("Discord channel not started")

        try:

            channel_id = int(target)
            channel = self._client.get_channel(channel_id)

            if not channel:
                channel = await self._client.fetch_channel(channel_id)

            if not channel:
                raise ValueError(f"Channel not found: {channel_id}")

            # For URLs, just send as message with caption
            content = f"{caption}\n{media_url}" if caption else media_url
            message = await channel.send(content=content)

            await self._track_send()
            return str(message.id)

        except Exception as e:
            logger.error(f"[{self.id}] Failed to send media: {e}")
            if self._connection_manager:
                self._connection_manager.metrics.record_error(str(e))
            raise

    async def _handle_discord_message(self, message: Any) -> None:
        """Handle incoming Discord message"""
        try:
            import discord

            # Determine chat type
            if isinstance(message.channel, discord.DMChannel):
                chat_type = "direct"
            elif isinstance(message.channel, discord.Thread):
                chat_type = "thread"
            else:
                chat_type = "group"

            # Create normalized message
            inbound = InboundMessage(
                channel_id=self.id,
                message_id=str(message.id),
                sender_id=str(message.author.id),
                sender_name=message.author.display_name or str(message.author.name),
                chat_id=str(message.channel.id),
                chat_type=chat_type,
                text=message.content,
                timestamp=message.created_at.isoformat(),
                reply_to=str(message.reference.message_id) if message.reference else None,
                metadata={
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "guild_name": message.guild.name if message.guild else None,
                    "channel_name": getattr(message.channel, "name", None),
                    "is_bot": message.author.bot,
                    "attachments": len(message.attachments),
                },
            )

            await self._handle_message(inbound)

        except Exception as e:
            logger.error(f"[{self.id}] Error handling message: {e}")
            if self._connection_manager:
                self._connection_manager.metrics.record_error(str(e))
