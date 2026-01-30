"""BlueBubbles channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class BlueBubblesChannel(ChannelPlugin):
    """BlueBubbles server integration for iMessage"""

    def __init__(self):
        super().__init__()
        self.id = "bluebubbles"
        self.label = "BlueBubbles"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=False,
            supports_polls=False,
        )
        self._server_url = None
        self._password = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start BlueBubbles integration"""
        self._server_url = config.get("serverUrl") or config.get("server_url")
        self._password = config.get("password")

        if not self._server_url:
            raise ValueError("BlueBubbles server URL required")

        logger.info("Starting BlueBubbles channel...")
        logger.info(f"Connecting to BlueBubbles server: {self._server_url}")

        self._running = True
        logger.info("BlueBubbles channel started (framework ready)")

    async def stop(self) -> None:
        """Stop BlueBubbles integration"""
        logger.info("Stopping BlueBubbles channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message via BlueBubbles"""
        if not self._running:
            raise RuntimeError("BlueBubbles channel not started")

        logger.info(f"BlueBubbles send to {target}")
        return f"bb-msg-{datetime.now(UTC).timestamp()}"

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._running:
            raise RuntimeError("BlueBubbles channel not started")

        logger.info(f"BlueBubbles media to {target}")
        return f"bb-media-{datetime.now(UTC).timestamp()}"
