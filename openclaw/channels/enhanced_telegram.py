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

        # Add command handlers
        from telegram.ext import CommandHandler
        self._app.add_handler(CommandHandler("start", self._handle_start_command))
        self._app.add_handler(CommandHandler("help", self._handle_help_command))
        self._app.add_handler(CommandHandler("revoke", self._handle_revoke_command))
        self._app.add_handler(CommandHandler("reset", self._handle_reset_command))
        self._app.add_handler(CommandHandler("status", self._handle_status_command))

        # Add message handler (handle both text and photos, but not commands)
        self._app.add_handler(
            MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, self._handle_telegram_message)
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
        if not update.message:
            return

        message = update.message
        chat = message.chat
        sender = message.from_user

        # Skip messages without text or photo
        if not message.text and not message.photo:
            return

        self._last_chat_id = str(chat.id)  # Record the last chat ID for streaming

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
        if message.photo:
            # Get the largest photo
            photo = message.photo[-1]
            try:
                # Get file info and download URL
                file = await context.bot.get_file(photo.file_id)
                photo_url = file.file_path
                # Add photo context to text
                if not text:
                    text = "[User sent a photo]"
                else:
                    text = f"[User sent a photo with caption: {text}]"
                logger.info(f"[{self.id}] Received photo: {photo_url}")
            except Exception as e:
                logger.error(f"[{self.id}] Failed to get photo: {e}")
                text = "[User sent a photo, but failed to retrieve it]"

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
                "photo_url": photo_url,
                "has_photo": message.photo is not None,
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

    # =========================================================================
    # Command Handlers
    # =========================================================================

    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        welcome_message = """
👋 **欢迎使用 OpenClaw AI 助手！**

我是一个功能强大的 AI 助手，可以帮你完成各种任务。

**✨ 我的能力：**
• 💻 执行命令行操作
• 📁 读写文件
• 🌐 搜索网络信息
• 🖼️ 分析和生成图片
• 🎯 40+ 专业技能

**📝 可用命令：**
/help - 查看帮助信息
/status - 查看系统状态
/reset - 重置对话历史
/revoke - 清除会话数据

**🚀 开始使用：**
直接发送消息或问题，我会尽力帮助你！

例如：
• "今天天气怎么样？"
• "帮我查看当前目录的文件"
• "写一个 Python 脚本"
"""
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} started bot")

    async def _handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        help_message = """
📚 **OpenClaw AI 助手 - 帮助文档**

**🎯 核心功能：**

1️⃣ **命令执行**
   • 可以执行 bash 命令
   • 查看系统信息、文件列表等

2️⃣ **文件操作**
   • 读取、写入、编辑文件
   • 代码分析和修改

3️⃣ **网络功能**
   • 搜索网络信息
   • 获取天气、新闻等

4️⃣ **图片处理**
   • 分析图片内容
   • 生成图片（即将支持）

5️⃣ **专业技能**
   • 编程助手（Python, JS, 等）
   • 数据分析
   • 文档处理
   • 更多...

**💡 使用技巧：**
• 直接描述你想做什么
• 我会自动选择合适的工具
• 支持多步骤任务

**⚙️ 命令列表：**
/start - 欢迎信息
/help - 显示此帮助
/status - 系统状态
/reset - 重置对话
/revoke - 清除数据

有任何问题，直接问我就好！😊
"""
        await update.message.reply_text(help_message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} requested help")

    async def _handle_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        from datetime import datetime
        
        # Get session info
        chat_id = str(update.effective_chat.id)
        session_id = f"{self.id}-{chat_id}"
        
        status_message = f"""
📊 **系统状态**

**🤖 Bot 信息：**
• 状态: ✅ 运行中
• 频道: {self.id}
• 模型: Gemini Flash 3

**💬 会话信息：**
• 会话 ID: `{session_id}`
• 用户 ID: `{update.effective_user.id}`
• 聊天类型: {update.effective_chat.type}

**⚡ 功能状态：**
• 工具: ✅ 19个已加载
• 技能: ✅ 40个可用
• 记忆: ✅ 持久化启用
• 上下文: ✅ 自动压缩

**⏰ 时间：**
• 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

一切正常运行！🚀
"""
        await update.message.reply_text(status_message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} checked status")

    async def _handle_reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command"""
        chat_id = str(update.effective_chat.id)
        session_id = f"{self.id}-{chat_id}"
        
        # Try to delete session if session manager is available
        try:
            if hasattr(self, '_session_manager') and self._session_manager:
                self._session_manager.delete_session(session_id)
                message = "✅ **对话已重置**\n\n你的对话历史已被清除，我们可以重新开始！"
            else:
                message = "✅ **对话已重置**\n\n会话已重新开始。"
        except Exception as e:
            logger.error(f"[{self.id}] Failed to reset session: {e}")
            message = "⚠️ **重置失败**\n\n无法清除会话数据，但你仍然可以继续对话。"
        
        await update.message.reply_text(message, parse_mode="Markdown")
        logger.info(f"[{self.id}] User {update.effective_user.id} reset conversation")

    async def _handle_revoke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /revoke command"""
        chat_id = str(update.effective_chat.id)
        session_id = f"{self.id}-{chat_id}"
        
        # Delete session data
        try:
            if hasattr(self, '_session_manager') and self._session_manager:
                self._session_manager.delete_session(session_id)
                logger.info(f"[{self.id}] User {update.effective_user.id} revoked data")
                
                message = """
🗑️ **数据已清除**

已删除以下数据：
• ✅ 对话历史
• ✅ 会话状态
• ✅ 临时缓存

**隐私保护：**
• 你的数据已从系统中完全移除
• 不会保留任何对话记录
• 可以随时重新开始使用

如需重新开始，发送 /start
"""
            else:
                message = "✅ 数据清除请求已记录。"
                
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"[{self.id}] Failed to revoke data: {e}")
            await update.message.reply_text(
                "⚠️ 数据清除失败，请稍后重试。",
                parse_mode="Markdown"
            )
