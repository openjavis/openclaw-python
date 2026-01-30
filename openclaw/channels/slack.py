"""Slack channel implementation"""

import logging
from datetime import datetime
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin, InboundMessage

logger = logging.getLogger(__name__)


class SlackChannel(ChannelPlugin):
    """Slack bot channel"""

    def __init__(self):
        super().__init__()
        self.id = "slack"
        self.label = "Slack"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group", "channel"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=True,
            supports_polls=False,
        )
        self._app: Any | None = None
        self._bot_token: str | None = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Slack bot"""
        self._bot_token = config.get("botToken") or config.get("bot_token")
        signing_secret = config.get("signingSecret") or config.get("signing_secret")

        if not self._bot_token or not signing_secret:
            raise ValueError("Slack bot token and signing secret required")

        logger.info("Starting Slack channel...")

        try:
            from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
            from slack_bolt.async_app import AsyncApp

            self._app = AsyncApp(token=self._bot_token, signing_secret=signing_secret)

            @self._app.message("")
            async def handle_message(message, say):
                await self._handle_slack_message(message, say)

            # Start socket mode handler
            app_token = config.get("appToken") or config.get("app_token")
            if app_token:
                handler = AsyncSocketModeHandler(self._app, app_token)
                await handler.start_async()

            self._running = True
            logger.info("Slack channel started")

        except ImportError:
            logger.error("slack-sdk not installed. Install with: pip install slack-sdk slack-bolt")
            raise

    async def stop(self) -> None:
        """Stop Slack bot"""
        logger.info("Stopping Slack channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._app:
            raise RuntimeError("Slack channel not started")

        try:
            result = await self._app.client.chat_postMessage(
                channel=target, text=text, thread_ts=reply_to
            )
            return result["ts"]

        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}", exc_info=True)
            raise

    async def _handle_slack_message(self, message: dict[str, Any], say: Any) -> None:
        """Handle incoming Slack message"""
        # Skip bot messages
        if message.get("bot_id"):
            return

        # Create normalized message
        inbound = InboundMessage(
            channel_id=self.id,
            message_id=message.get("ts", ""),
            sender_id=message.get("user", ""),
            sender_name=message.get("user", ""),  # TODO: Fetch user info
            chat_id=message.get("channel", ""),
            chat_type="group" if message.get("channel_type") in ["group", "channel"] else "direct",
            text=message.get("text", ""),
            timestamp=datetime.fromtimestamp(float(message.get("ts", 0))).isoformat(),
            reply_to=message.get("thread_ts"),
            metadata={"channel_type": message.get("channel_type"), "team": message.get("team")},
        )

        await self._handle_message(inbound)
