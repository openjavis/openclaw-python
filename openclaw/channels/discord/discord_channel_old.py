"""Discord channel implementation"""

import asyncio
import logging
from typing import Any

from .base import ChannelPlugin, InboundMessage

logger = logging.getLogger(__name__)


class DiscordChannel(ChannelPlugin):
    """
    Discord channel plugin.
    
    Provides Discord bot integration using discord.py library.
    """
    
    def __init__(self):
        super().__init__()
        self._client = None
        self._running = False
    
    @property
    def channel_id(self) -> str:
        return "discord"
    
    async def start(self, config: dict[str, Any]) -> None:
        """
        Start Discord bot.
        
        Config:
            token: Discord bot token (from env: DISCORD_BOT_TOKEN)
            allow_from: List of allowed user IDs
            guild_id: Guild (server) ID to operate in
        """
        try:
            import discord
            from discord.ext import commands
        except ImportError:
            logger.error("discord.py not installed. Install with: pip install discord.py")
            raise
        
        token = config.get("token") or self._get_env_var("DISCORD_BOT_TOKEN")
        if not token:
            raise ValueError("Discord bot token not found (set DISCORD_BOT_TOKEN)")
        
        allow_from = config.get("allow_from", [])
        
        # Create bot with command prefix
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        self._client = commands.Bot(command_prefix="!", intents=intents)
        
        @self._client.event
        async def on_ready():
            logger.info(f"Discord bot logged in as {self._client.user}")
            self._running = True
        
        @self._client.event
        async def on_message(message: discord.Message):
            # Ignore bot's own messages
            if message.author == self._client.user:
                return
            
            # Check allow list
            if allow_from and str(message.author.id) not in allow_from:
                logger.debug(f"Ignoring message from unauthorized user: {message.author.id}")
                return
            
            # Create inbound message
            inbound = InboundMessage(
                message_id=str(message.id),
                channel_id="discord",
                sender_id=str(message.author.id),
                text=message.content,
                metadata={
                    "username": str(message.author),
                    "guild_id": str(message.guild.id) if message.guild else None,
                    "channel_id": str(message.channel.id),
                    "attachments": [att.url for att in message.attachments],
                },
            )
            
            # Handle message through callback
            if self.message_callback:
                await self.message_callback(inbound)
        
        # Run bot in background
        asyncio.create_task(self._client.start(token))
        
        # Wait for ready
        while not self._running:
            await asyncio.sleep(0.1)
        
        logger.info("Discord channel started")
    
    async def stop(self) -> None:
        """Stop Discord bot"""
        if self._client:
            await self._client.close()
            self._running = False
        logger.info("Discord channel stopped")
    
    async def send_text(
        self, target: str, text: str, reply_to: str | None = None
    ) -> str:
        """
        Send text message to Discord channel or user.
        
        Args:
            target: Channel ID or user ID (format: "channel:123" or "user:456")
            text: Message text
            reply_to: Message ID to reply to
        
        Returns:
            Message ID
        """
        if not self._client:
            raise RuntimeError("Discord channel not started")
        
        # Parse target
        if target.startswith("channel:"):
            channel_id = int(target.split(":", 1)[1])
            channel = self._client.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel not found: {channel_id}")
        elif target.startswith("user:"):
            user_id = int(target.split(":", 1)[1])
            user = await self._client.fetch_user(user_id)
            channel = await user.create_dm()
        else:
            # Assume it's a channel ID
            channel_id = int(target)
            channel = self._client.get_channel(channel_id)
            if not channel:
                raise ValueError(f"Channel not found: {channel_id}")
        
        # Send message
        if reply_to:
            # Fetch message to reply to
            try:
                ref_message = await channel.fetch_message(int(reply_to))
                message = await ref_message.reply(text)
            except:
                # Fallback to normal send
                message = await channel.send(text)
        else:
            message = await channel.send(text)
        
        return str(message.id)
    
    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """
        Send media (photo/video/file) to Discord.
        
        Args:
            target: Channel or user ID
            media_url: URL or path to media
            media_type: Type (photo/video/document)
            caption: Optional caption
        
        Returns:
            Message ID
        """
        if not self._client:
            raise RuntimeError("Discord channel not started")
        
        # Parse target same as send_text
        if target.startswith("channel:"):
            channel_id = int(target.split(":", 1)[1])
            channel = self._client.get_channel(channel_id)
        elif target.startswith("user:"):
            user_id = int(target.split(":", 1)[1])
            user = await self._client.fetch_user(user_id)
            channel = await user.create_dm()
        else:
            channel_id = int(target)
            channel = self._client.get_channel(channel_id)
        
        # Send file
        import discord
        
        if media_url.startswith("http"):
            # URL - Discord will fetch it
            message = await channel.send(content=caption, file=discord.File(media_url))
        else:
            # Local file
            with open(media_url, "rb") as f:
                file = discord.File(f, filename=media_url.split("/")[-1])
                message = await channel.send(content=caption, file=file)
        
        return str(message.id)
