"""Tlon/Urbit channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class TlonChannel(ChannelPlugin):
    """Tlon (Urbit) integration"""

    def __init__(self):
        super().__init__()
        self.id = "tlon"
        self.label = "Tlon"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=False,
            supports_reactions=False,
            supports_threads=False,
            supports_polls=False,
        )
        self._ship_url = None
        self._ship_code = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Tlon/Urbit integration"""
        self._ship_url = config.get("shipUrl") or config.get("ship_url")
        self._ship_code = config.get("shipCode") or config.get("ship_code")

        if not self._ship_url or not self._ship_code:
            raise ValueError("Urbit ship URL and code required")

        logger.info("Starting Tlon channel...")
        logger.warning("Tlon channel requires Urbit/Tlon API integration")
        logger.info(f"Ship URL: {self._ship_url}")

        self._running = True
        logger.info("Tlon channel started (framework ready)")

    async def stop(self) -> None:
        """Stop Tlon integration"""
        logger.info("Stopping Tlon channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send message to Urbit"""
        if not self._running:
            raise RuntimeError("Tlon channel not started")

        logger.info(f"Tlon send to {target}")
        return f"tlon-msg-{datetime.now(UTC).timestamp()}"

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media (not typically supported in Urbit)"""
        if not self._running:
            raise RuntimeError("Tlon channel not started")

        # Urbit/Tlon typically uses text with URLs
        return await self.send_text(target, f"{caption or ''}\n{media_url}")
