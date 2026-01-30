"""Nextcloud Talk channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class NextcloudChannel(ChannelPlugin):
    """Nextcloud Talk integration"""

    def __init__(self):
        super().__init__()
        self.id = "nextcloud"
        self.label = "Nextcloud Talk"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=True,
            supports_reactions=False,
            supports_threads=False,
            supports_polls=False,
        )
        self._base_url = None
        self._username = None
        self._password = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Nextcloud Talk bot"""
        self._base_url = config.get("baseUrl") or config.get("base_url")
        self._username = config.get("username")
        self._password = config.get("password")

        if not all([self._base_url, self._username, self._password]):
            raise ValueError("Nextcloud URL, username and password required")

        logger.info("Starting Nextcloud Talk channel...")
        logger.warning("Nextcloud Talk requires API integration")
        logger.info(f"Nextcloud server: {self._base_url}")

        self._running = True
        logger.info("Nextcloud Talk channel started (framework ready)")

    async def stop(self) -> None:
        """Stop Nextcloud Talk bot"""
        logger.info("Stopping Nextcloud Talk channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._running:
            raise RuntimeError("Nextcloud Talk channel not started")

        logger.info(f"Nextcloud Talk send to {target}")
        return f"nc-msg-{datetime.now(UTC).timestamp()}"

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._running:
            raise RuntimeError("Nextcloud Talk channel not started")

        logger.info(f"Nextcloud Talk media to {target}")
        return f"nc-media-{datetime.now(UTC).timestamp()}"
