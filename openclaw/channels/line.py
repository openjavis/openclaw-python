"""LINE channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class LINEChannel(ChannelPlugin):
    """LINE Messaging API integration"""

    def __init__(self):
        super().__init__()
        self.id = "line"
        self.label = "LINE"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=True,
            supports_reactions=False,
            supports_threads=False,
            supports_polls=False,
        )
        self._api = None
        self._channel_secret = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start LINE bot"""
        channel_access_token = config.get("channelAccessToken") or config.get(
            "channel_access_token"
        )
        self._channel_secret = config.get("channelSecret") or config.get("channel_secret")

        if not channel_access_token or not self._channel_secret:
            raise ValueError("LINE channel access token and secret required")

        logger.info("Starting LINE channel...")

        try:
            from linebot import LineBotApi
            from linebot.models import TextSendMessage

            self._api = LineBotApi(channel_access_token)

            # Test API
            profile = self._api.get_bot_info()
            logger.info(f"LINE bot: {profile.display_name}")

            self._running = True
            logger.info("LINE channel started")

        except ImportError:
            logger.warning("line-bot-sdk not installed")
            logger.warning("Install with: pip install line-bot-sdk")
            self._running = True  # Framework mode
            logger.info("LINE channel started (framework mode)")
        except Exception as e:
            logger.error(f"Failed to start LINE channel: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop LINE bot"""
        logger.info("Stopping LINE channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._running:
            raise RuntimeError("LINE channel not started")

        if not self._api:
            logger.warning("LINE API not initialized")
            return f"line-msg-{datetime.now(UTC).timestamp()}"

        try:
            from linebot.models import TextSendMessage

            if reply_to:
                # Reply to message
                self._api.reply_message(reply_to, TextSendMessage(text=text))
            else:
                # Push message
                self._api.push_message(target, TextSendMessage(text=text))

            return f"line-msg-{datetime.now(UTC).timestamp()}"

        except Exception as e:
            logger.error(f"LINE send error: {e}", exc_info=True)
            raise

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._running:
            raise RuntimeError("LINE channel not started")

        if not self._api:
            logger.warning("LINE API not initialized")
            return f"line-media-{datetime.now(UTC).timestamp()}"

        try:
            from linebot.models import AudioSendMessage, ImageSendMessage, VideoSendMessage

            if media_type.startswith("image"):
                message = ImageSendMessage(
                    original_content_url=media_url, preview_image_url=media_url
                )
            elif media_type.startswith("video"):
                message = VideoSendMessage(
                    original_content_url=media_url, preview_image_url=media_url
                )
            elif media_type.startswith("audio"):
                message = AudioSendMessage(original_content_url=media_url, duration=60000)
            else:
                # Fallback to text
                message = TextSendMessage(text=f"{caption or 'Media'}: {media_url}")

            self._api.push_message(target, message)
            return f"line-media-{datetime.now(UTC).timestamp()}"

        except Exception as e:
            logger.error(f"LINE media send error: {e}", exc_info=True)
            raise
