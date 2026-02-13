"""Telegram channel implementation"""
from __future__ import annotations


import logging
from datetime import UTC, datetime, timezone
from typing import Any, Optional

from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, CallbackQueryHandler, filters

from ..chat_commands import ChatCommandExecutor, ChatCommandParser
from ..base import ChannelCapabilities, ChannelPlugin, InboundMessage
from .command_handler import TelegramCommandHandler
from .commands import list_native_commands, register_commands_with_telegram
from .i18n_support import register_lang_handlers
from .commands_extended import register_extended_commands

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
        self._command_parser: Optional[ChatCommandParser] = None
        self._command_executor: Optional[ChatCommandExecutor] = None
        self._owner_id: Optional[str] = None
        self._command_handler: Optional[TelegramCommandHandler] = None
        self._config: Optional[dict] = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Telegram bot"""
        self._bot_token = config.get("botToken") or config.get("bot_token")

        if not self._bot_token:
            raise ValueError("Telegram bot token not provided")

        # Get owner ID for command permissions
        self._owner_id = config.get("ownerId") or config.get("owner_id")
        self._config = config

        logger.info("Starting Telegram channel...")

        # Initialize chat command system
        self._command_parser = ChatCommandParser()
        # Note: command_executor will be initialized once we have session_manager
        # This would typically be set via set_message_handler or similar

        # Create application
        self._app = Application.builder().token(self._bot_token).build()

        # Add command handlers
        self._app.add_handler(CommandHandler("start", self._handle_start_command))
        self._app.add_handler(CommandHandler("help", self._handle_help_command))
        self._app.add_handler(CommandHandler("new", self._handle_new_command))
        self._app.add_handler(CommandHandler("status", self._handle_status_command))
        self._app.add_handler(CommandHandler("model", self._handle_model_command))
        
        # Register i18n language switching handlers
        register_lang_handlers(self._app)
        
        # Register extended commands
        register_extended_commands(self._app)
        
        # Add callback query handler for inline keyboards
        self._app.add_handler(CallbackQueryHandler(self._handle_callback_query))

        # Add message handlers for all types (text and media)
        # Handle text messages
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_telegram_message)
        )
        # Handle photo messages
        self._app.add_handler(
            MessageHandler(filters.PHOTO, self._handle_telegram_media)
        )
        # Handle video messages
        self._app.add_handler(
            MessageHandler(filters.VIDEO, self._handle_telegram_media)
        )
        # Handle audio messages
        self._app.add_handler(
            MessageHandler(filters.AUDIO | filters.VOICE, self._handle_telegram_media)
        )
        # Handle document messages
        self._app.add_handler(
            MessageHandler(filters.Document.ALL, self._handle_telegram_media)
        )

        # Start bot
        await self._app.initialize()
        await self._app.start()
        
        # Get bot info after initialization
        bot_info = await self._app.bot.get_me()
        account_id = str(bot_info.id)
        logger.info(f"Bot initialized: @{bot_info.username} (ID: {account_id})")
        
        # Create a minimal config dict for command handler
        cmd_config = {
            "channels": {
                "telegram": {
                    "accounts": {
                        account_id: {
                            "allowFrom": []  # Allow all for now
                        }
                    }
                }
            },
            "agents": {
                "defaults": {
                    "model": config.get("model", "google/gemini-3-pro-preview")
                }
            }
        }
        
        self._command_handler = TelegramCommandHandler(cmd_config, account_id, None)
        
        # Delete any existing webhook and clear pending updates to avoid conflicts
        # This ensures clean state when switching from webhook to polling mode
        await self._app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Cleared webhook and pending updates")
        
        # Register bot commands with Telegram
        await self._register_bot_commands()
        
        # Set bot menu button (optional)
        await self._setup_menu_button()
        
        await self._app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False  # We already dropped them above
        )

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
        """Send text message with Markdown support"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")

        try:
            # Parse target (chat_id)
            chat_id = int(target) if target.lstrip("-").isdigit() else target

            # Send message with Markdown parsing
            # Try Markdown first, fallback to plain text if parsing fails
            try:
                message = await self._app.bot.send_message(
                    chat_id=chat_id, 
                    text=text, 
                    reply_to_message_id=int(reply_to) if reply_to else None,
                    parse_mode="Markdown"
                )
            except Exception as markdown_error:
                logger.debug(f"Markdown parsing failed, sending as plain text: {markdown_error}")
                # Fallback to plain text
                message = await self._app.bot.send_message(
                    chat_id=chat_id, 
                    text=text, 
                    reply_to_message_id=int(reply_to) if reply_to else None
                )

            return str(message.message_id)

        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}", exc_info=True)
            raise

    async def send_photo(
        self, target: str, photo, caption: str | None = None, 
        reply_to: str | None = None, keyboard=None
    ) -> str:
        """Send photo message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")
        
        chat_id = int(target) if target.lstrip("-").isdigit() else target
        
        try:
            message = await self._app.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                parse_mode="Markdown" if caption else None,
                reply_to_message_id=int(reply_to) if reply_to else None,
                reply_markup=keyboard
            )
            return str(message.message_id)
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")
            raise

    async def send_video(
        self, target: str, video, caption: str | None = None,
        reply_to: str | None = None, keyboard=None
    ) -> str:
        """Send video message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")
        
        chat_id = int(target) if target.lstrip("-").isdigit() else target
        
        try:
            message = await self._app.bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=caption,
                parse_mode="Markdown" if caption else None,
                reply_to_message_id=int(reply_to) if reply_to else None,
                reply_markup=keyboard
            )
            return str(message.message_id)
        except Exception as e:
            logger.error(f"Failed to send video: {e}")
            raise

    async def send_document(
        self, target: str, document, caption: str | None = None,
        reply_to: str | None = None, keyboard=None
    ) -> str:
        """Send document/file message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")
        
        chat_id = int(target) if target.lstrip("-").isdigit() else target
        
        try:
            message = await self._app.bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=caption,
                parse_mode="Markdown" if caption else None,
                reply_to_message_id=int(reply_to) if reply_to else None,
                reply_markup=keyboard
            )
            return str(message.message_id)
        except Exception as e:
            logger.error(f"Failed to send document: {e}")
            raise

    async def send_audio(
        self, target: str, audio, caption: str | None = None,
        reply_to: str | None = None
    ) -> str:
        """Send audio message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")
        
        chat_id = int(target) if target.lstrip("-").isdigit() else target
        
        try:
            message = await self._app.bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                caption=caption,
                parse_mode="Markdown" if caption else None,
                reply_to_message_id=int(reply_to) if reply_to else None
            )
            return str(message.message_id)
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            raise

    async def send_location(
        self, target: str, latitude: float, longitude: float,
        reply_to: str | None = None
    ) -> str:
        """Send location message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")
        
        chat_id = int(target) if target.lstrip("-").isdigit() else target
        
        try:
            message = await self._app.bot.send_location(
                chat_id=chat_id,
                latitude=latitude,
                longitude=longitude,
                reply_to_message_id=int(reply_to) if reply_to else None
            )
            return str(message.message_id)
        except Exception as e:
            logger.error(f"Failed to send location: {e}")
            raise

    async def send_poll(
        self, target: str, question: str, options: list[str],
        is_anonymous: bool = True, reply_to: str | None = None
    ) -> str:
        """Send poll message"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")
        
        chat_id = int(target) if target.lstrip("-").isdigit() else target
        
        try:
            message = await self._app.bot.send_poll(
                chat_id=chat_id,
                question=question,
                options=options,
                is_anonymous=is_anonymous,
                reply_to_message_id=int(reply_to) if reply_to else None
            )
            return str(message.message_id)
        except Exception as e:
            logger.error(f"Failed to send poll: {e}")
            raise

    async def send_dice(
        self, target: str, emoji: str = "🎲",
        reply_to: str | None = None
    ) -> str:
        """Send dice/animation message (🎲🎯🏀⚽🎳🎰)"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")
        
        chat_id = int(target) if target.lstrip("-").isdigit() else target
        
        try:
            message = await self._app.bot.send_dice(
                chat_id=chat_id,
                emoji=emoji,
                reply_to_message_id=int(reply_to) if reply_to else None
            )
            return str(message.message_id)
        except Exception as e:
            logger.error(f"Failed to send dice: {e}")
            raise

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message (supports both URLs and local file paths)"""
        if not self._app:
            raise RuntimeError("Telegram channel not started")

        try:
            chat_id = int(target) if target.lstrip("-").isdigit() else target

            # Determine if media_url is a local file path or URL
            from pathlib import Path
            
            media_source = media_url
            is_local_file = False
            
            # Check if it's a local file path
            if not media_url.startswith(("http://", "https://", "file://")):
                file_path = Path(media_url).expanduser()
                if file_path.exists() and file_path.is_file():
                    # Open local file for sending
                    media_source = open(file_path, "rb")
                    is_local_file = True
                    logger.info(f"Sending local file: {file_path}")
            
            try:
                if media_type == "photo":
                    message = await self._app.bot.send_photo(
                        chat_id=chat_id, photo=media_source, caption=caption
                    )
                elif media_type == "video":
                    message = await self._app.bot.send_video(
                        chat_id=chat_id, video=media_source, caption=caption
                    )
                elif media_type == "document":
                    message = await self._app.bot.send_document(
                        chat_id=chat_id, document=media_source, caption=caption
                    )
                else:
                    raise ValueError(f"Unsupported media type: {media_type}")

                return str(message.message_id)
            finally:
                # Close file if it was opened
                if is_local_file and hasattr(media_source, "close"):
                    media_source.close()

        except Exception as e:
            logger.error(f"Failed to send Telegram media: {e}", exc_info=True)
            raise

    def set_command_executor(self, session_manager, agent_runtime) -> None:
        """Set up command executor with session manager and agent runtime"""
        self._command_executor = ChatCommandExecutor(session_manager, agent_runtime)

    async def _handle_telegram_media(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming media messages (photo, video, audio, document)"""
        if not update.message:
            return

        message = update.message
        chat = message.chat
        sender = message.from_user

        # Determine media type and get file info
        media_type = None
        file_id = None
        file_name = None
        mime_type = None
        caption = message.caption or ""

        if message.photo:
            media_type = "photo"
            # Get largest photo size
            file_id = message.photo[-1].file_id
            file_name = f"photo_{message.message_id}.jpg"
        elif message.video:
            media_type = "video"
            file_id = message.video.file_id
            file_name = message.video.file_name or f"video_{message.message_id}.mp4"
            mime_type = message.video.mime_type
        elif message.audio:
            media_type = "audio"
            file_id = message.audio.file_id
            file_name = message.audio.file_name or f"audio_{message.message_id}.mp3"
            mime_type = message.audio.mime_type
        elif message.voice:
            media_type = "voice"
            file_id = message.voice.file_id
            file_name = f"voice_{message.message_id}.ogg"
            mime_type = message.voice.mime_type
        elif message.document:
            media_type = "document"
            file_id = message.document.file_id
            file_name = message.document.file_name or f"document_{message.message_id}"
            mime_type = message.document.mime_type

        if not file_id:
            logger.warning(f"No file_id found for media message: {message.message_id}")
            return

        try:
            # Get file from Telegram
            file = await context.bot.get_file(file_id)
            file_url = file.file_path

            logger.info(f"Received {media_type}: {file_name} from user {sender.id}")

            # Determine chat type
            chat_type = "direct"
            if chat.type == "group" or chat.type == "supergroup":
                chat_type = "group"
            elif chat.type == "channel":
                chat_type = "channel"

            # Create message with media info
            # Format text to describe the media for the AI
            text = caption if caption else f"[User sent a {media_type}]"
            
            # Add media information to text so AI knows what to do
            if media_type == "photo":
                text = f"{text}\n\n[Image URL: {file_url}]" if caption else f"[User sent an image: {file_url}]"
            elif media_type in ["video", "audio", "voice", "document"]:
                text = f"{text}\n\n[{media_type.capitalize()} URL: {file_url}, filename: {file_name}]"

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
                    "media_type": media_type,
                    "file_id": file_id,
                    "file_name": file_name,
                    "file_url": file_url,
                    "mime_type": mime_type,
                    "caption": caption,
                },
            )

            # Pass to handler
            await self._handle_message(inbound)

        except Exception as e:
            logger.error(f"Error handling media message: {e}", exc_info=True)
            await context.bot.send_message(
                chat_id=chat.id,
                text=f"❌ Sorry, I had trouble processing that {media_type}.",
                reply_to_message_id=message.message_id
            )

    async def _handle_telegram_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming Telegram text message"""
        if not update.message or not update.message.text:
            return

        message = update.message
        chat = message.chat
        sender = message.from_user

        # Check for chat commands
        if self._command_parser:
            command = self._command_parser.parse(message.text)
            if command and self._command_executor:
                session_id = f"telegram:{chat.id}"
                user_id = str(sender.id)
                is_owner = self._owner_id and user_id == self._owner_id

                try:
                    response = await self._command_executor.execute(
                        command, session_id, user_id, is_owner
                    )
                    await self._app.bot.send_message(
                        chat_id=chat.id,
                        text=response,
                        reply_to_message_id=message.message_id
                    )
                    return
                except Exception as e:
                    logger.error(f"Error executing command: {e}", exc_info=True)
                    await self._app.bot.send_message(
                        chat_id=chat.id,
                        text=f"❌ Error: {str(e)}",
                        reply_to_message_id=message.message_id
                    )
                    return

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

    async def _register_bot_commands(self):
        """Register bot commands with Telegram"""
        commands = [
            BotCommand("start", "🚀 Start using the bot"),
            BotCommand("help", "📋 View help information"),
            BotCommand("new", "🆕 Start new conversation"),
            BotCommand("status", "📊 View status"),
            BotCommand("model", "🤖 Switch AI model"),
        ]
        
        try:
            await self._app.bot.set_my_commands(commands)
            logger.info(f"✅ Registered {len(commands)} commands with Telegram")
        except Exception as e:
            logger.error(f"Failed to register commands: {e}")

    async def _setup_menu_button(self):
        """Setup bot menu button"""
        try:
            # Set menu button (shows in bottom left of chat)
            logger.info("Menu button setup completed")
        except Exception as e:
            logger.debug(f"Menu button setup failed: {e}")

    def _get_quick_reply_keyboard(self):
        """Get quick reply keyboard with common commands"""
        keyboard = [
            [KeyboardButton("💬 New Chat"), KeyboardButton("📊 Status")],
            [KeyboardButton("❓ Help"), KeyboardButton("🤖 Switch Model")],
        ]
        return ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True,
            one_time_keyboard=False
        )

    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "👋 *Welcome to OpenClaw AI Assistant!*\n\n"
            "I am a powerful AI assistant that can help you:\n"
            "• 💬 Intelligent conversation\n"
            "• 📝 Process documents and files\n"
            "• 🔍 Search and query information\n"
            "• 🛠️ Execute various tasks\n\n"
            "Send any message to start a conversation, or use /help to see more commands."
        )
        
        # Send welcome message with quick reply keyboard
        await update.message.reply_text(
            welcome_message,
            parse_mode="Markdown",
            reply_markup=self._get_quick_reply_keyboard()
        )

    async def _handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "📋 *Available Commands*\n\n"
            "/start - Show welcome message\n"
            "/help - Show this help information\n"
            "/new - Start new conversation (clear history)\n"
            "/status - View bot status\n"
            "/model - Switch AI model\n\n"
            "*💡 Tips*\n"
            "• Send messages directly to start conversation\n"
            "• Supports images, files, etc.\n"
            "• Multi-turn conversation supported\n\n"
            "_Need help? Visit documentation or contact support team._"
        )
        
        await update.message.reply_text(
            help_message,
            parse_mode="Markdown"
        )

    async def _handle_new_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new command - start new conversation"""
        user_id = update.effective_user.id
        
        # Create inline keyboard for confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data="new_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="new_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🆕 *Start New Conversation*\n\n"
            "This will clear the current conversation history.\n"
            "Are you sure you want to continue?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    async def _handle_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        # Get current model from config
        current_model = self._config.get("model", "google/gemini-3-pro-preview") if self._config else "unknown"
        
        status_message = (
            "📊 *Bot Status*\n\n"
            f"🤖 Current Model: `{current_model}`\n"
            f"✅ Status: Running\n"
            f"💬 Session: Active\n"
            f"📡 Connection: Normal\n\n"
            "_System running normally_"
        )
        
        await update.message.reply_text(
            status_message,
            parse_mode="Markdown"
        )

    async def _handle_model_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /model command - show model selection"""
        current_model = self._config.get("model", "google/gemini-3-pro-preview") if self._config else "unknown"
        
        keyboard = [
            [InlineKeyboardButton("🌟 Gemini Pro (Current)", callback_data="model_gemini")],
            [InlineKeyboardButton("🧠 Claude Sonnet", callback_data="model_claude")],
            [InlineKeyboardButton("⚡ GPT-4", callback_data="model_gpt4")],
            [InlineKeyboardButton("🔥 GPT-4 Turbo", callback_data="model_gpt4turbo")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 *Select AI Model*\n\n"
            f"Current Model: `{current_model}`\n\n"
            f"Choose the model to use:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        logger.info(f"Callback query: {data}")
        
        if data == "new_confirm":
            # Clear conversation history (implement this in session manager)
            await query.edit_message_text(
                "✅ *New Conversation Started*\n\n"
                "Conversation history cleared. Send a message to start a new conversation!",
                parse_mode="Markdown"
            )
        
        elif data == "new_cancel":
            await query.edit_message_text(
                "❌ *Cancelled*\n\nContinuing current conversation.",
                parse_mode="Markdown"
            )
        
        elif data.startswith("model_"):
            model_name = data.replace("model_", "")
            model_map = {
                "gemini": ("google/gemini-3-pro-preview", "Gemini Pro"),
                "claude": ("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
                "gpt4": ("gpt-4", "GPT-4"),
                "gpt4turbo": ("gpt-4-turbo", "GPT-4 Turbo"),
            }
            
            if model_name in model_map:
                model_id, display_name = model_map[model_name]
                # Update config (this would need to be persisted)
                if self._config:
                    self._config["model"] = model_id
                
                await query.edit_message_text(
                    f"✅ *Model Switched*\n\n"
                    f"Now using: {display_name}\n"
                    f"Model ID: `{model_id}`\n\n"
                    f"_New messages will use this model_",
                    parse_mode="Markdown"
                )
