"""Matrix channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class MatrixChannel(ChannelPlugin):
    """Matrix protocol channel"""

    def __init__(self):
        super().__init__()
        self.id = "matrix"
        self.label = "Matrix"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=False,
            supports_polls=False,
        )
        self._client = None
        self._homeserver: str | None = None
        self._user_id: str | None = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Matrix client"""
        self._homeserver = config.get("homeserver", "https://matrix.org")
        self._user_id = config.get("userId") or config.get("user_id")
        password = config.get("password")
        access_token = config.get("accessToken") or config.get("access_token")

        if not self._user_id:
            raise ValueError("Matrix user ID not provided")

        logger.info("Starting Matrix channel...")

        try:
            from nio import AsyncClient

            self._client = AsyncClient(self._homeserver, self._user_id)

            # Login
            if access_token:
                self._client.access_token = access_token
            elif password:
                response = await self._client.login(password)
                if not response or hasattr(response, "message"):
                    raise RuntimeError(f"Matrix login failed: {response}")
            else:
                raise ValueError("Matrix password or access_token required")

            # Start syncing
            # TODO: Add message callback and sync loop

            self._running = True
            logger.info("Matrix channel started")

        except ImportError:
            logger.error("matrix-nio not installed. Install with: pip install matrix-nio")
            raise
        except Exception as e:
            logger.error(f"Failed to start Matrix channel: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop Matrix client"""
        if self._client:
            logger.info("Stopping Matrix channel...")
            await self._client.close()
            self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._client or not self._running:
            raise RuntimeError("Matrix channel not started")

        try:
            # Send message to room
            response = await self._client.room_send(
                room_id=target,
                message_type="m.room.message",
                content={"msgtype": "m.text", "body": text},
            )

            if hasattr(response, "event_id"):
                return response.event_id
            else:
                raise RuntimeError("Failed to send Matrix message")

        except Exception as e:
            logger.error(f"Failed to send Matrix message: {e}", exc_info=True)
            raise

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._client or not self._running:
            raise RuntimeError("Matrix channel not started")

        # TODO: Implement Matrix media sending
        # Requires uploading to Matrix content repository first
        logger.warning(f"Matrix send_media not fully implemented: {target}")
        return f"matrix-media-{datetime.now(UTC).timestamp()}"
