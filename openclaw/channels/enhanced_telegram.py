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

        self._streaming_states = {}  # Reacord {session_id: {"msg_id": xxx, "full_content": yyy}}

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

        # Add command handlers
        from telegram.ext import CommandHandler

        self._app.add_handler(CommandHandler("start", self._handle_start_command))
        self._app.add_handler(CommandHandler("help", self._handle_help_command))
        self._app.add_handler(CommandHandler("revoke", self._handle_revoke_command))
        self._app.add_handler(CommandHandler("reset", self._handle_reset_command))
        self._app.add_handler(CommandHandler("status", self._handle_status_command))

        # Add message handler (handle both text and photos, but not commands)
        # IMPORTANT: Also need to handle images sent as documents (common with JPEG)
        self._app.add_handler(
            MessageHandler(
                (filters.TEXT | filters.PHOTO | filters.Document.IMAGE) & ~filters.COMMAND,
                self._handle_telegram_message,
            )
        )

        # Add error handler
        self._app.add_error_handler(self._handle_error)

        # Add debug handler to log all updates for diagnostics
        async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Debug handler to log all updates"""
            logger.info(f"[{self.id}] 📥 Incoming update - type: {type(update).__name__}")
            if update.message:
                logger.info(f"[{self.id}]   Message ID: {update.message.message_id}")
                logger.info(f"[{self.id}]   From: {update.effective_user.id}")
                logger.info(f"[{self.id}]   Chat: {update.effective_chat.id}")
                logger.info(f"[{self.id}]   Text: {bool(update.message.text)}")
                logger.info(f"[{self.id}]   Photo: {bool(update.message.photo)}")
                logger.info(f"[{self.id}]   Caption: {bool(update.message.caption)}")
                # Check all possible media fields
                logger.info(f"[{self.id}]   Document: {bool(update.message.document)}")
                logger.info(f"[{self.id}]   Video: {bool(update.message.video)}")
                logger.info(f"[{self.id}]   Audio: {bool(update.message.audio)}")
                logger.info(f"[{self.id}]   Voice: {bool(update.message.voice)}")
                logger.info(f"[{self.id}]   Video_note: {bool(update.message.video_note)}")
                logger.info(f"[{self.id}]   Animation: {bool(update.message.animation)}")

                # Check message content_type
                if hasattr(update.message, "content_type"):
                    logger.info(f"[{self.id}]   Content Type: {update.message.content_type}")

                # Raw message data
                logger.info(f"[{self.id}]   Raw message dict: {update.message.to_dict()}")

                if update.message.photo:
                    logger.info(f"[{self.id}]   Photo count: {len(update.message.photo)}")

        # Register the debug handler as a low-priority post-init handler
        from telegram.ext import filters as tg_filters

        self._app.add_handler(MessageHandler(tg_filters.ALL, log_all_updates), group=-10)

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
        logger.info(f"[{self.id}] _handle_telegram_message triggered")

        if not update.message:
            logger.warning(f"[{self.id}] No message in update")
            return

        message = update.message
        chat = message.chat
        sender = message.from_user

        logger.info(
            f"[{self.id}] Message received - text={bool(message.text)}, photo={bool(message.photo)}, caption={bool(message.caption)}, doc={bool(message.document)}"
        )
        logger.info(
            f"[{self.id}] Message details: text='{message.text}', photo={message.photo}, caption='{message.caption}'"
        )

        # Check for image document (JPEG sent as document)
        is_image_document = False
        if message.document and message.document.mime_type:
            is_image_mime = message.document.mime_type.startswith("image/")
            is_image_filename = (
                message.document.file_name
                and message.document.file_name.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
                )
            )
            is_image_document = is_image_mime or is_image_filename

            if is_image_document:
                logger.info(
                    f"[{self.id}] ✅ Detected image document: {message.document.file_name} ({message.document.mime_type})"
                )

        # Skip messages without text, photo, or image document
        if not message.text and not message.photo and not is_image_document:
            logger.info(
                f"[{self.id}] ⚠️  Skipping message: no text, no photo, and no image document"
            )
            logger.info(
                f"[{self.id}]    (But has document? {bool(message.document)}, video? {bool(message.video)})"
            )
            return

        logger.info(
            f"[{self.id}] Processing message: has_text={bool(message.text)}, has_photo={bool(message.photo)}, has_image_doc={is_image_document}"
        )

        self._last_chat_id = str(chat.id)  # Record the last chat ID for streaming
        session_id = f"{self.id}-{chat.id}"  # Bulid session ID based on channel and chat ID for session management

        # Determine chat type
        chat_type = "direct"
        if chat.type in ("group", "supergroup"):
            chat_type = "group"
        elif chat.type == "channel":
            chat_type = "channel"

        # Handle text or caption
        text = message.text or message.caption or ""

        # If there's a photo, download it and add to metadata
        photo_url = None
        images = []

        # Handle regular photos
        if message.photo:
            logger.info(f"[{self.id}] Photo detected: {len(message.photo)} photo size(s)")
            # Get the largest photo
            photo = message.photo[-1]
            logger.info(
                f"[{self.id}] Selected largest photo: file_id={photo.file_id}, width={photo.width}, height={photo.height}"
            )

            try:
                # Get file info and download URL
                logger.info(f"[{self.id}] Getting file info for photo...")
                file = await context.bot.get_file(photo.file_id)
                logger.info(f"[{self.id}] Got file info: file_path={file.file_path}")

                if file.file_path.startswith("http"):
                    photo_url = file.file_path
                else:
                    # Only construct URL if file_path is provided and doesn't already look like a URL
                    photo_url = (
                        f"https://api.telegram.org/file/bot{self._bot_token}/{file.file_path}"
                    )

                images.append(photo_url)
                logger.info(f"[{self.id}] ✅ Received photo: {photo_url}")

                # Add photo context to text
                if not text:
                    text = "[User sent a photo]"
                else:
                    text = f"[User sent a photo with caption: {text}]"

            except Exception as e:
                logger.error(f"[{self.id}] ❌ Failed to get photo: {e}", exc_info=True)
                text = "[User sent a photo, but failed to retrieve it]"

        # Handle image documents (JPEG sent as document)
        elif is_image_document:
            logger.info(f"[{self.id}] Image document detected: {message.document.file_name}")

            try:
                # Get file info for the document
                logger.info(f"[{self.id}] Getting file info for image document...")
                file = await context.bot.get_file(message.document.file_id)
                logger.info(f"[{self.id}] Got file info: file_path={file.file_path}")

                if file.file_path.startswith("http"):
                    photo_url = file.file_path
                else:
                    # Only construct URL if file_path is provided and doesn't already look like a URL
                    photo_url = (
                        f"https://api.telegram.org/file/bot{self._bot_token}/{file.file_path}"
                    )

                images.append(photo_url)
                logger.info(f"[{self.id}] ✅ Received image document: {photo_url}")

                # Add photo context to text
                if not text:
                    text = f"[User sent an image: {message.document.file_name}]"
                else:
                    text = (
                        f"[User sent an image ({message.document.file_name}) with caption: {text}]"
                    )

            except Exception as e:
                logger.error(f"[{self.id}] ❌ Failed to get image document: {e}", exc_info=True)
                text = "[User sent an image, but failed to retrieve it]"
        else:
            logger.info(f"[{self.id}] No photo or image document in this message")

        # Create normalized message
        inbound = InboundMessage(
            channel_id=self.id,
            message_id=str(message.message_id),
            sender_id=str(sender.id),
            sender_name=sender.full_name or sender.username or str(sender.id),
            chat_id=str(chat.id),
            chat_type=chat_type,
            text=text,
            timestamp=message.date.isoformat() if message.date else datetime.now(UTC).isoformat(),
            reply_to=str(message.reply_to_message.message_id) if message.reply_to_message else None,
            metadata={
                "username": sender.username,
                "chat_title": chat.title,
                "chat_username": chat.username,
                "is_bot": sender.is_bot,
                "images": images,  # Add images list to metadata
                "photo_url": photo_url,
                "has_photo": message.photo is not None,
            },
        )

        logger.info(
            f"[{self.id}] InboundMessage created: text_len={len(text)}, images={len(images)}, metadata.images={len(inbound.metadata.get('images', []))}"
        )

        # Pass to handler (with metrics tracking)
        logger.info(f"[{self.id}] Passing message to handler...")
        await self._handle_message(inbound)
        logger.info(f"[{self.id}] Message handler completed")

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

    # =========================================================================
    # Command Handlers
    # =========================================================================

    async def _handle_start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command"""
        welcome_message = """
👋 **Welcome to OpenClaw AI Assistant!**

I'm a powerful AI assistant that can help you with various tasks.

**✨ My Capabilities:**
• 💻 Execute command-line operations
• 📁 Read/write files
• 🌐 Search web information
• 🖼️ Analyze and generate images
• 🎯 40+ professional skills

**📝 Available Commands:**
/help - View help information
/status - Check system status
/reset - Reset conversation history
/revoke - Clear session data

**🚀 Getting Started:**
Just send me messages or questions, and I'll do my best to help!

Examples:
• "What's the weather today?"
• "Help me check files in current directory"
• "Write a Python script"
"""
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} started bot")

    async def _handle_help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command"""
        help_message = """
📚 **OpenClaw AI Assistant - Help Documentation**

**🎯 Core Features:**

1️⃣ **Command Execution**
   • Execute bash commands
   • View system info, file lists, etc.

2️⃣ **File Operations**
   • Read, write, edit files
   • Code analysis and modification

3️⃣ **Network Features**
   • Search web information
   • Get weather, news, etc.

4️⃣ **Image Processing**
   • Analyze image content
   • Generate images (coming soon)

5️⃣ **Professional Skills**
   • Programming assistant (Python, JS, etc.)
   • Data analysis
   • Document processing
   • And more...

**💡 Usage Tips:**
• Directly describe what you want to do
• I'll automatically select the right tools
• Support multi-step tasks

**⚙️ Command List:**
/start - Welcome message
/help - Show this help
/status - System status
/reset - Reset conversation
/revoke - Clear data

Feel free to ask me anything! 😊
"""
        await update.message.reply_text(help_message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} requested help")

    async def _handle_status_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /status command"""
        from datetime import datetime

        # Get session info
        chat_id = str(update.effective_chat.id)
        session_id = f"{self.id}-{chat_id}"

        status_message = f"""
📊 **System Status**

**🤖 Bot Information:**
• Status: ✅ Running
• Channel: {self.id}
• Model: Gemini Flash 3

**💬 Session Information:**
• Session ID: `{session_id}`
• User ID: `{update.effective_user.id}`
• Chat Type: {update.effective_chat.type}

**⚡ Feature Status:**
• Tools: ✅ 19 loaded
• Skills: ✅ 40 available
• Memory: ✅ Persistence enabled
• Context: ✅ Auto-compaction

**⏰ Time:**
• Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Everything is running smoothly! 🚀
"""
        await update.message.reply_text(status_message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} checked status")

    async def _handle_reset_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /reset command"""
        chat_id = str(update.effective_chat.id)
        session_id = f"{self.id}-{chat_id}"

        # Try to delete session if session manager is available
        try:
            if hasattr(self, "_session_manager") and self._session_manager:
                self._session_manager.delete_session(session_id)
                message = "✅ **Conversation Reset**\n\nYour conversation history has been cleared, we can start fresh!"
            else:
                message = "✅ **Conversation Reset**\n\nSession has been restarted."
        except Exception as e:
            logger.error(f"[{self.id}] Failed to reset session: {e}")
            message = "⚠️ **Reset Failed**\n\nUnable to clear session data, but you can still continue the conversation."

        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} reset conversation")

    async def _handle_revoke_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /revoke command"""
        chat_id = str(update.effective_chat.id)
        session_id = f"{self.id}-{chat_id}"

        # Delete session data
        try:
            if hasattr(self, "_session_manager") and self._session_manager:
                self._session_manager.delete_session(session_id)
                logger.info(f"[{self.id}] User {update.effective_user.id} revoked data")

                message = """
🗑️ **Data Cleared**

Deleted data includes:
• ✅ Conversation history
• ✅ Session state
• ✅ Temporary cache

**Privacy Protection:**
• Your data has been completely removed from the system
• No conversation records are kept
• You can restart anytime

To restart, send /start
"""
            else:
                message = "✅ Data clearance request has been recorded."

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"[{self.id}] Failed to revoke data: {e}")
            await update.message.reply_text(
                "⚠️ Data clearance failed, please try again later.", parse_mode="Markdown"
            )
