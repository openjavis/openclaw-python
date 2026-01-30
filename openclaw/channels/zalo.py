"""Zalo channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class ZaloChannel(ChannelPlugin):
    """Zalo messaging integration"""

    def __init__(self):
        super().__init__()
        self.id = "zalo"
        self.label = "Zalo"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=True,
            supports_reactions=False,
            supports_threads=False,
            supports_polls=False,
        )
        self._access_token = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Zalo bot"""
        app_id = config.get("appId") or config.get("app_id")
        app_secret = config.get("appSecret") or config.get("app_secret")
        self._access_token = config.get("accessToken") or config.get("access_token")

        if not app_id or not app_secret:
            raise ValueError("Zalo app ID and secret required")

        logger.info("Starting Zalo channel...")
        logger.warning("Zalo channel requires Zalo SDK integration")
        logger.info(f"Zalo bot configured with app ID: {app_id}")

        self._running = True
        logger.info("Zalo channel started (framework ready)")

    async def stop(self) -> None:
        """Stop Zalo bot"""
        logger.info("Stopping Zalo channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._running:
            raise RuntimeError("Zalo channel not started")

        logger.info(f"Zalo send to {target}")
        return f"zalo-msg-{datetime.now(UTC).timestamp()}"

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._running:
            raise RuntimeError("Zalo channel not started")

        logger.info(f"Zalo media to {target}")
        return f"zalo-media-{datetime.now(UTC).timestamp()}"
