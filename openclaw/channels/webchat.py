"""WebChat channel (Gateway WebSocket)"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin, InboundMessage

logger = logging.getLogger(__name__)


class WebChatChannel(ChannelPlugin):
    """WebChat channel via Gateway WebSocket"""

    def __init__(self):
        super().__init__()
        self.id = "webchat"
        self.label = "WebChat"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct"],
            supports_media=False,
            supports_reactions=False,
            supports_threads=False,
            supports_polls=False,
        )
        self._gateway_server: Any | None = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start WebChat (actually handled by Gateway)"""
        logger.info("WebChat channel ready")
        self._running = True

    async def stop(self) -> None:
        """Stop WebChat"""
        logger.info("WebChat channel stopped")
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message (via Gateway broadcast)"""
        # WebChat messages are broadcast via Gateway events
        # This is handled by the Gateway server
        if self._gateway_server:
            await self._gateway_server.broadcast_event(
                "chat",
                {
                    "channel": self.id,
                    "target": target,
                    "text": text,
                    "messageId": f"webchat-{datetime.now(UTC).timestamp()}",
                },
            )

        return f"webchat-{datetime.now(UTC).timestamp()}"

    def set_gateway_server(self, server: Any) -> None:
        """Set reference to Gateway server"""
        self._gateway_server = server

    async def handle_webchat_message(
        self, session_key: str, text: str, sender_id: str = "webchat-user"
    ) -> None:
        """Handle WebChat message from Gateway"""
        inbound = InboundMessage(
            channel_id=self.id,
            message_id=f"webchat-{datetime.now(UTC).timestamp()}",
            sender_id=sender_id,
            sender_name="WebChat User",
            chat_id=session_key,
            chat_type="direct",
            text=text,
            timestamp=datetime.now(UTC).isoformat(),
            metadata={"session_key": session_key},
        )

        await self._handle_message(inbound)
