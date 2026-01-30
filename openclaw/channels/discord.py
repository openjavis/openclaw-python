"""Discord channel implementation"""

import asyncio
import logging
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin, InboundMessage

logger = logging.getLogger(__name__)


class DiscordChannel(ChannelPlugin):
    """Discord bot channel"""

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

    async def start(self, config: dict[str, Any]) -> None:
        """Start Discord bot"""
        self._bot_token = config.get("botToken") or config.get("bot_token")

        if not self._bot_token:
            raise ValueError("Discord bot token not provided")

        logger.info("Starting Discord channel...")

        try:
            import discord
            from discord.ext import commands

            intents = discord.Intents.default()
            intents.message_content = True
            intents.messages = True

            self._client = commands.Bot(command_prefix="!", intents=intents)

            @self._client.event
            async def on_ready():
                logger.info(f"Discord bot logged in as {self._client.user}")
                self._running = True

            @self._client.event
            async def on_message(message):
                if message.author == self._client.user:
                    return

                # Ignore bot commands
                if message.content.startswith("!"):
                    return

                await self._handle_discord_message(message)

            # Start bot in background
            asyncio.create_task(self._client.start(self._bot_token))

        except ImportError:
            logger.error("discord.py not installed. Install with: pip install discord.py")
            raise

    async def stop(self) -> None:
        """Stop Discord bot"""
        if self._client:
            logger.info("Stopping Discord channel...")
            await self._client.close()
            self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._client:
            raise RuntimeError("Discord channel not started")

        try:
            # Parse target as channel ID
            channel_id = int(target)
            channel = self._client.get_channel(channel_id)

            if not channel:
                raise ValueError(f"Channel not found: {channel_id}")

            # Send message
            message = await channel.send(text)
            return str(message.id)

        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}", exc_info=True)
            raise

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._client:
            raise RuntimeError("Discord channel not started")

        try:
            import discord

            channel_id = int(target)
            channel = self._client.get_channel(channel_id)

            if not channel:
                raise ValueError(f"Channel not found: {channel_id}")

            # Send with file URL
            message = await channel.send(content=caption, file=discord.File(media_url))
            return str(message.id)

        except Exception as e:
            logger.error(f"Failed to send Discord media: {e}", exc_info=True)
            raise

    async def _handle_discord_message(self, message: Any) -> None:
        """Handle incoming Discord message"""
        # Determine chat type
        chat_type = "direct" if isinstance(message.channel, type(None)) else "group"

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
                "channel_name": message.channel.name if hasattr(message.channel, "name") else None,
            },
        )

        await self._handle_message(inbound)
