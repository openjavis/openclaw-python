"""Signal channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class SignalChannel(ChannelPlugin):
    """Signal messaging channel"""

    def __init__(self):
        super().__init__()
        self.id = "signal"
        self.label = "Signal"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=False,
            supports_polls=False,
        )
        self._bot = None
        self._phone_number: str | None = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Signal bot"""
        self._phone_number = config.get("phoneNumber") or config.get("phone_number")

        if not self._phone_number:
            raise ValueError("Signal phone number not provided")

        logger.info("Starting Signal channel...")

        try:
            # Signal-cli integration via subprocess
            import shutil
            import subprocess

            # Check if signal-cli is installed
            signal_cli = shutil.which("signal-cli")
            if not signal_cli:
                logger.warning("signal-cli not found in PATH")
                logger.warning("Install from: https://github.com/AsamK/signal-cli")
                self._running = True  # Allow framework mode
                logger.info(
                    "Signal channel started (framework mode - signal-cli needed for full functionality)"
                )
                return

            # Test signal-cli
            result = subprocess.run([signal_cli, "--version"], capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"signal-cli found: {result.stdout.strip()}")
                self._running = True
                logger.info(f"Signal channel ready for {self._phone_number}")
            else:
                logger.warning("signal-cli found but not functioning properly")
                self._running = True

        except Exception as e:
            logger.error(f"Failed to start Signal channel: {e}", exc_info=True)
            # Still mark as running in framework mode
            self._running = True
            logger.info("Signal channel started (framework mode)")

    async def stop(self) -> None:
        """Stop Signal bot"""
        logger.info("Stopping Signal channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._running:
            raise RuntimeError("Signal channel not started")

        # TODO: Implement actual Signal message sending via signal-cli
        logger.warning(f"Signal send_text not implemented: {target}")
        return f"signal-msg-{datetime.now(UTC).timestamp()}"

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._running:
            raise RuntimeError("Signal channel not started")

        # TODO: Implement Signal media sending
        logger.warning(f"Signal send_media not implemented: {target}")
        return f"signal-media-{datetime.now(UTC).timestamp()}"


# Note: Full Signal implementation requires:
# 1. signal-cli installed and configured
# 2. DBus integration or REST API
# 3. Message receiving via signal-cli daemon
# 4. Python wrapper like python-signalbot or custom signal-cli integration
