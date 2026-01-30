"""Base channel plugin interface"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from .connection import (
    ConnectionManager,
    ConnectionMetrics,
    ConnectionState,
    HealthChecker,
    ReconnectConfig,
)

logger = logging.getLogger(__name__)


class ChannelCapabilities(BaseModel):
    """Channel capabilities"""

    chat_types: list[str] = ["direct", "group"]  # Supported chat types
    supports_media: bool = False
    supports_reactions: bool = False
    supports_threads: bool = False
    supports_polls: bool = False


class InboundMessage(BaseModel):
    """Normalized inbound message"""

    channel_id: str
    message_id: str
    sender_id: str
    sender_name: str
    chat_id: str
    chat_type: str  # "direct", "group", "channel"
    text: str
    timestamp: str
    reply_to: str | None = None
    metadata: dict[str, Any] = {}


class OutboundMessage(BaseModel):
    """Message to send"""

    channel_id: str
    target: str  # Chat/user ID
    text: str
    reply_to: str | None = None
    metadata: dict[str, Any] = {}


# Type alias for message handler
MessageHandler = Callable[[InboundMessage], Awaitable[None]]


class ChannelPlugin(ABC):
    """Base class for channel plugins with enhanced connection management"""

    def __init__(self):
        self.id: str = ""
        self.label: str = ""
        self.capabilities: ChannelCapabilities = ChannelCapabilities()
        self._message_handler: MessageHandler | None = None
        self._running: bool = False

        # Connection management
        self._connection_manager: ConnectionManager | None = None
        self._health_checker: HealthChecker | None = None
        self._config: dict[str, Any] = {}

    def _setup_connection_manager(self, reconnect_config: ReconnectConfig | None = None) -> None:
        """
        Setup connection manager for automatic reconnection

        Call this in subclass __init__ or start() if you want
        automatic reconnection support.
        """
        self._connection_manager = ConnectionManager(
            channel_id=self.id,
            connect_fn=self._do_connect,
            disconnect_fn=self._do_disconnect,
            reconnect_config=reconnect_config or ReconnectConfig(),
        )

    def _setup_health_checker(self, interval: float = 30.0, timeout: float = 10.0) -> None:
        """
        Setup health checker

        Call this in subclass start() after connection is established.
        """
        self._health_checker = HealthChecker(
            channel_id=self.id, check_fn=self._health_check, interval=interval, timeout=timeout
        )
        self._health_checker.set_unhealthy_callback(self._on_unhealthy)

    async def _do_connect(self) -> None:
        """
        Internal connection implementation

        Override this in subclass instead of start() if using
        connection manager.
        """
        raise NotImplementedError("Subclass must implement _do_connect")

    async def _do_disconnect(self) -> None:
        """
        Internal disconnection implementation

        Override this in subclass instead of stop() if using
        connection manager.
        """
        raise NotImplementedError("Subclass must implement _do_disconnect")

    async def _health_check(self) -> bool:
        """
        Perform health check

        Override in subclass to implement actual health check.
        Default implementation just checks if running.
        """
        return self._running

    async def _on_unhealthy(self) -> None:
        """
        Called when channel becomes unhealthy

        Override in subclass to handle unhealthy state.
        Default triggers reconnection if connection manager is set.
        """
        logger.warning(f"[{self.id}] Channel unhealthy, attempting reconnection")
        if self._connection_manager:
            self._connection_manager.handle_connection_error(Exception("Health check failed"))

    @abstractmethod
    async def start(self, config: dict[str, Any]) -> None:
        """Start the channel"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel"""
        pass

    @abstractmethod
    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message. Returns message ID."""
        pass

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message. Returns message ID."""
        raise NotImplementedError("Media not supported by this channel")

    def set_message_handler(self, handler: MessageHandler) -> None:
        """Set handler for inbound messages"""
        self._message_handler = handler

    async def _handle_message(self, message: InboundMessage) -> None:
        """Internal message handler with metrics tracking"""
        if self._connection_manager:
            self._connection_manager.metrics.record_message_received()

        if self._message_handler:
            try:
                await self._message_handler(message)
            except Exception as e:
                logger.error(f"[{self.id}] Message handler error: {e}")
                if self._connection_manager:
                    self._connection_manager.metrics.record_error(str(e))

    async def _track_send(self) -> None:
        """Track sent message in metrics"""
        if self._connection_manager:
            self._connection_manager.metrics.record_message_sent()

    def is_running(self) -> bool:
        """Check if channel is running"""
        return self._running

    def is_connected(self) -> bool:
        """Check if channel is connected"""
        if self._connection_manager:
            return self._connection_manager.is_connected
        return self._running

    def is_healthy(self) -> bool:
        """Check if channel is healthy"""
        if self._health_checker:
            return self._health_checker.is_healthy
        return self._running

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state"""
        if self._connection_manager:
            return self._connection_manager.state
        return ConnectionState.CONNECTED if self._running else ConnectionState.DISCONNECTED

    def get_metrics(self) -> ConnectionMetrics | None:
        """Get connection metrics"""
        if self._connection_manager:
            return self._connection_manager.metrics
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with enhanced status"""
        result = {
            "id": self.id,
            "label": self.label,
            "capabilities": self.capabilities.model_dump(),
            "running": self._running,
            "connected": self.is_connected(),
            "healthy": self.is_healthy(),
            "state": self.get_connection_state().value,
        }

        # Add metrics if available
        if self._connection_manager:
            result["metrics"] = self._connection_manager.metrics.to_dict()

        # Add health info if available
        if self._health_checker:
            result["health"] = self._health_checker.to_dict()

        return result
