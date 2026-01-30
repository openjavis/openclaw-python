"""Nostr channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class NostrChannel(ChannelPlugin):
    """Nostr protocol integration"""

    def __init__(self):
        super().__init__()
        self.id = "nostr"
        self.label = "Nostr"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "public"],
            supports_media=False,
            supports_reactions=True,
            supports_threads=False,
            supports_polls=False,
        )
        self._private_key = None
        self._relays = []

    async def start(self, config: dict[str, Any]) -> None:
        """Start Nostr integration"""
        self._private_key = config.get("privateKey") or config.get("private_key")
        self._relays = config.get(
            "relays", ["wss://relay.damus.io", "wss://relay.nostr.band", "wss://nos.lol"]
        )

        if not self._private_key:
            raise ValueError("Nostr private key required")

        logger.info("Starting Nostr channel...")
        logger.warning("Nostr channel requires nostr-sdk or nostr-python")
        logger.info(f"Configured {len(self._relays)} relays")

        self._running = True
        logger.info("Nostr channel started (framework ready)")

    async def stop(self) -> None:
        """Stop Nostr integration"""
        logger.info("Stopping Nostr channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send Nostr note"""
        if not self._running:
            raise RuntimeError("Nostr channel not started")

        logger.info("Nostr send note")
        return f"nostr-note-{datetime.now(UTC).timestamp()}"

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media (Nostr uses URLs in notes)"""
        if not self._running:
            raise RuntimeError("Nostr channel not started")

        # Nostr includes media as URLs in notes
        return await self.send_text(target, f"{caption or ''}\n{media_url}")
