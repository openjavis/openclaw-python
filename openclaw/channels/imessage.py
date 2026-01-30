"""iMessage channel implementation for macOS"""

import logging
import platform
import subprocess
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class iMessageChannel(ChannelPlugin):
    """iMessage integration using AppleScript (macOS only)"""

    def __init__(self):
        super().__init__()
        self.id = "imessage"
        self.label = "iMessage"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=False,
            supports_polls=False,
        )
        self._is_macos = platform.system() == "Darwin"

    async def start(self, config: dict[str, Any]) -> None:
        """Start iMessage integration"""
        if not self._is_macos:
            raise RuntimeError("iMessage channel requires macOS")

        logger.info("Starting iMessage channel...")

        try:
            # Test if Messages app is accessible
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Messages" to get name'],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                logger.info("Messages.app accessible")
                self._running = True
                logger.info("iMessage channel started")
            else:
                raise RuntimeError("Cannot access Messages.app")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Messages.app not responding")
        except FileNotFoundError:
            raise RuntimeError("osascript not found (macOS required)")
        except Exception as e:
            logger.error(f"Failed to start iMessage channel: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop iMessage integration"""
        logger.info("Stopping iMessage channel...")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message via iMessage"""
        if not self._running:
            raise RuntimeError("iMessage channel not started")

        try:
            # Escape quotes in text
            escaped_text = text.replace('"', '\\"').replace("'", "\\'")

            # AppleScript to send message
            script = f"""
            tell application "Messages"
                set targetService to 1st service whose service type = iMessage
                set targetBuddy to buddy "{target}" of targetService
                send "{escaped_text}" to targetBuddy
            end tell
            """

            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                message_id = f"imsg-{int(datetime.now(UTC).timestamp()*1000)}"
                logger.info(f"Sent iMessage to {target}")
                return message_id
            else:
                error = result.stderr or "Unknown error"
                raise RuntimeError(f"Failed to send message: {error}")

        except Exception as e:
            logger.error(f"iMessage send error: {e}", exc_info=True)
            raise

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message (limited support)"""
        if not self._running:
            raise RuntimeError("iMessage channel not started")

        logger.warning("iMessage media sending has limited AppleScript support")
        # iMessage media sending via AppleScript is complex
        # Would need to save file locally first, then send as attachment
        return await self.send_text(target, caption or f"[Media: {media_url}]")
