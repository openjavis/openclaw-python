"""
Enhanced Telegram channel with connection management
"""

import asyncio
import logging
from datetime import UTC, datetime, timezone
from typing import Any

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from .base import ChannelCapabilities, ChannelPlugin, InboundMessage
from .connection import ReconnectConfig

logger = logging.getLogger(__name__)


class EnhancedTelegramChannel(ChannelPlugin):
    """
    Enhanced Telegram bot channel with:
    - Automatic reconnection
    - Health checking
    - Connection metrics
    - Better error handling
    """

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
        self._polling_task: asyncio.Task | None = None

        self._streaming_states = (
            {}
        )  # Reacord {session_id: {"msg_id": xxx, "full_content": yyy}}

        # Setup connection manager with reconnection
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
        """Start Telegram bot with connection management"""
        self._config = config
        self._bot_token = config.get("botToken") or config.get("bot_token")

        if not self._bot_token:
            raise ValueError("Telegram bot token not provided")

        logger.info(f"[{self.id}] Starting Telegram channel...")

        # Use connection manager for connection
        if self._connection_manager:
            success = await self._connection_manager.connect()
            if success:
                # Setup health checker after connection
                self._setup_health_checker(interval=60.0, timeout=15.0)
                if self._health_checker:
                    self._health_checker.start()
        else:
            # Fallback to direct connection
            await self._do_connect()

    async def _do_connect(self) -> None:
        """Internal connection implementation"""
        if self._app:
            # Clean up existing connection
            await self._do_disconnect()

        # Create application
        self._app = Application.builder().token(self._bot_token).build()

        # Add message handler
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_telegram_message)
        )

        # Add error handler
        self._app.add_error_handler(self._handle_error)

        # Start bot
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling(
            drop_pending_updates=True, allowed_updates=["message", "edited_message"]
        )

        self._running = True
        logger.info(f"[{self.id}] Telegram channel connected")

    async def _do_disconnect(self) -> None:
        """Internal disconnection implementation"""
        if self._app:
            try:
                if self._app.updater.running:
                    await self._app.updater.stop()
                if self._app.running:
                    await self._app.stop()
                await self._app.shutdown()
            except Exception as e:
                logger.warning(f"[{self.id}] Error during disconnect: {e}")
            finally:
                self._app = None

        self._running = False

    async def _health_check(self) -> bool:
        """Check if Telegram connection is healthy"""
        if not self._app or not self._running:
            return False

        try:
            # Try to get bot info as health check
            me = await asyncio.wait_for(self._app.bot.get_me(), timeout=10.0)
            return me is not None
        except Exception as e:
            logger.warning(f"[{self.id}] Health check failed: {e}")
            return False

    async def stop(self) -> None:
        """Stop Telegram bot"""
        logger.info(f"[{self.id}] Stopping Telegram channel...")

        # Stop health checker
        if self._health_checker:
            self._health_checker.stop()

        # Stop connection
        if self._connection_manager:
            await self._connection_manager.disconnect()
        else:
            await self._do_disconnect()

        logger.info(f"[{self.id}] Telegram channel stopped")

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message with retry"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")

        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # Parse target (chat_id)
                chat_id = int(target) if target.lstrip("-").isdigit() else target

                # Send message
                message = await self._app.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_to_message_id=int(reply_to) if reply_to else None,
                )

                # Track metrics
                await self._track_send()

                return str(message.message_id)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"[{self.id}] Send failed (attempt {attempt + 1}/{max_retries}): {e}"
                )

                # Record error in metrics
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
            elif media_type == "audio":
                message = await self._app.bot.send_audio(
                    chat_id=chat_id, audio=media_url, caption=caption
                )
            elif media_type == "voice":
                message = await self._app.bot.send_voice(
                    chat_id=chat_id, voice=media_url, caption=caption
                )
            else:
                raise ValueError(f"Unsupported media type: {media_type}")

            await self._track_send()
            return str(message.message_id)

        except Exception as e:
            logger.error(f"[{self.id}] Failed to send media: {e}")
            if self._connection_manager:
                self._connection_manager.metrics.record_error(str(e))
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

        self._last_chat_id = str(chat.id)  # Record the last chat ID for streaming

        # Determine chat type
        chat_type = "direct"
        if chat.type in ("group", "supergroup"):
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
                "is_bot": sender.is_bot,
            },
        )

        # Pass to handler (with metrics tracking)
        await self._handle_message(inbound)

    # [NEW] Deal with streaming text updates
    async def on_event(self, event: Any) -> None:
        # ensure the text delta event
        if str(event.type).lower() != "eventtype.agent_text":
            if str(event.type).lower() == "eventtype.agent_turn_complete":
                # done with this session, clean up state
                self._streaming_states.pop(event.session_id, None)
            return

        text = event.data.get("delta", {}).get("text", "")
        session_id = event.session_id

        if not text or not hasattr(self, "_last_chat_id"):
            return

        # Check if we have an existing message to edit
        if session_id not in self._streaming_states:
            # 1. No existing message, send a new one
            msg_id = await self.send_text(self._last_chat_id, text)
            # 2. Record the message ID and full content
            self._streaming_states[session_id] = {"msg_id": msg_id, "full_content": text}
        else:
            # 3. Existing message, append text and edit
            state = self._streaming_states[session_id]
            state["full_content"] += text

            try:
                await self._app.bot.edit_message_text(
                    chat_id=int(self._last_chat_id),
                    message_id=int(state["msg_id"]),
                    text=state["full_content"],
                )
            except Exception as e:
                # Log but ignore edit errors
                if "Message is not modified" not in str(e):
                    logger.warning(f"Fail to edit message: {e}")

    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle Telegram errors"""
        error = context.error
        logger.error(f"[{self.id}] Telegram error: {error}")

        if self._connection_manager:
            self._connection_manager.metrics.record_error(str(error))

            # Trigger reconnection for connection errors
            error_str = str(error).lower()
            if any(x in error_str for x in ["network", "connection", "timeout"]):
                self._connection_manager.handle_connection_error(error)
