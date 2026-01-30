"""Telegram channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from .base import ChannelCapabilities, ChannelPlugin, InboundMessage

logger = logging.getLogger(__name__)


class TelegramChannel(ChannelPlugin):
    """Telegram bot channel"""

    def __init__(self):
        super().__init__()
        self.id = "telegram"
        self.label = "Telegram"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group", "channel"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=False,
            supports_polls=True,
        )
        self._app: Application | None = None
        self._bot_token: str | None = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Telegram bot"""
        self._bot_token = config.get("botToken") or config.get("bot_token")

        if not self._bot_token:
            raise ValueError("Telegram bot token not provided")

        logger.info("Starting Telegram channel...")

        # Create application
        self._app = Application.builder().token(self._bot_token).build()

        # Add message handler
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_telegram_message)
        )

        # Start bot
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()

        self._running = True
        logger.info("Telegram channel started")

    async def stop(self) -> None:
        """Stop Telegram bot"""
        if self._app:
            logger.info("Stopping Telegram channel...")
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            self._running = False
            logger.info("Telegram channel stopped")

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")

        try:
            # Parse target (chat_id)
            chat_id = int(target) if target.lstrip("-").isdigit() else target

            # Send message
            message = await self._app.bot.send_message(
                chat_id=chat_id, text=text, reply_to_message_id=int(reply_to) if reply_to else None
            )

            return str(message.message_id)

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}", exc_info=True)
            raise

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")

        try:
            chat_id = int(target) if target.lstrip("-").isdigit() else target

            if media_type == "photo":
                message = await self._app.bot.send_photo(
                    chat_id=chat_id, photo=media_url, caption=caption
                )
            elif media_type == "video":
                message = await self._app.bot.send_video(
                    chat_id=chat_id, video=media_url, caption=caption
                )
            elif media_type == "document":
                message = await self._app.bot.send_document(
                    chat_id=chat_id, document=media_url, caption=caption
                )
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            return str(message.message_id)

        except Exception as e:
            logger.error(f"Failed to send Telegram media: {e}", exc_info=True)
            raise

    async def _handle_telegram_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming Telegram message"""
        if not update.message or not update.message.text:
            return

        message = update.message
        chat = message.chat
        sender = message.from_user

        # Determine chat type
        chat_type = "direct"
        if chat.type == "group" or chat.type == "supergroup":
            chat_type = "group"
        elif chat.type == "channel":
            chat_type = "channel"

        # Create normalized message
        inbound = InboundMessage(
            channel_id=self.id,
            message_id=str(message.message_id),
            sender_id=str(sender.id),
            sender_name=sender.full_name or sender.username or str(sender.id),
            chat_id=str(chat.id),
            chat_type=chat_type,
            text=message.text,
            timestamp=message.date.isoformat() if message.date else datetime.now(UTC).isoformat(),
            reply_to=str(message.reply_to_message.message_id) if message.reply_to_message else None,
            metadata={
                "username": sender.username,
                "chat_title": chat.title,
                "chat_username": chat.username,
            },
        )

        # Pass to handler
        await self._handle_message(inbound)
