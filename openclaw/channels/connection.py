"""
Connection management for channels
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Channel connection states"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class ConnectionMetrics:
    """Connection metrics and statistics"""

    connected_at: datetime | None = None
    disconnected_at: datetime | None = None
    reconnect_count: int = 0
    last_reconnect_at: datetime | None = None
    messages_sent: int = 0
    messages_received: int = 0
    errors_count: int = 0
    last_error: str | None = None
    last_error_at: datetime | None = None
    last_heartbeat: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "disconnected_at": self.disconnected_at.isoformat() if self.disconnected_at else None,
            "reconnect_count": self.reconnect_count,
            "last_reconnect_at": (
                self.last_reconnect_at.isoformat() if self.last_reconnect_at else None
            ),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "errors_count": self.errors_count,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at.isoformat() if self.last_error_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "uptime_seconds": self.get_uptime_seconds(),
        }

    def get_uptime_seconds(self) -> float | None:
        """Get uptime in seconds"""
        if self.connected_at:
            end_time = self.disconnected_at or datetime.now(UTC)
            return (end_time - self.connected_at).total_seconds()
        return None

    def record_error(self, error: str) -> None:
        """Record an error"""
        self.errors_count += 1
        self.last_error = error
        self.last_error_at = datetime.now(UTC)

    def record_message_sent(self) -> None:
        """Record sent message"""
        self.messages_sent += 1

    def record_message_received(self) -> None:
        """Record received message"""
        self.messages_received += 1

    def record_heartbeat(self) -> None:
        """Record heartbeat"""
        self.last_heartbeat = datetime.now(UTC)


@dataclass
class ReconnectConfig:
    """Configuration for reconnection behavior"""

    enabled: bool = True
    max_attempts: int = 5
    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # 5 minutes
    exponential_backoff: bool = True
    jitter: bool = True  # Add randomness to prevent thundering herd


class ConnectionManager:
    """
    Manages connection lifecycle with reconnection support
    """

    def __init__(
        self,
        channel_id: str,
        connect_fn: Callable[[], Awaitable[None]],
        disconnect_fn: Callable[[], Awaitable[None]],
        reconnect_config: ReconnectConfig | None = None,
    ):
        """
        Initialize connection manager

        Args:
            channel_id: Channel identifier
            connect_fn: Async function to establish connection
            disconnect_fn: Async function to close connection
            reconnect_config: Reconnection configuration
        """
        self.channel_id = channel_id
        self._connect_fn = connect_fn
        self._disconnect_fn = disconnect_fn
        self._config = reconnect_config or ReconnectConfig()

        self._state = ConnectionState.DISCONNECTED
        self._metrics = ConnectionMetrics()
        self._reconnect_task: asyncio.Task | None = None
        self._current_attempt = 0
        self._state_callbacks: list[Callable[[ConnectionState], Awaitable[None]]] = []
        self._should_stop = False

    @property
    def state(self) -> ConnectionState:
        """Get current connection state"""
        return self._state

    @property
    def metrics(self) -> ConnectionMetrics:
        """Get connection metrics"""
        return self._metrics

    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._state == ConnectionState.CONNECTED

    def add_state_callback(self, callback: Callable[[ConnectionState], Awaitable[None]]) -> None:
        """Add callback for state changes"""
        self._state_callbacks.append(callback)

    async def _set_state(self, new_state: ConnectionState) -> None:
        """Update state and notify callbacks"""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            logger.info(f"[{self.channel_id}] State: {old_state.value} -> {new_state.value}")

            for callback in self._state_callbacks:
                try:
                    await callback(new_state)
                except Exception as e:
                    logger.error(f"State callback error: {e}")

    async def connect(self) -> bool:
        """
        Establish connection

        Returns:
            True if connected successfully
        """
        if self._state == ConnectionState.CONNECTED:
            return True

        self._should_stop = False
        await self._set_state(ConnectionState.CONNECTING)

        try:
            await self._connect_fn()
            await self._set_state(ConnectionState.CONNECTED)
            self._metrics.connected_at = datetime.now(UTC)
            self._metrics.disconnected_at = None
            self._current_attempt = 0
            logger.info(f"[{self.channel_id}] Connected successfully")
            return True

        except Exception as e:
            self._metrics.record_error(str(e))
            await self._set_state(ConnectionState.ERROR)
            logger.error(f"[{self.channel_id}] Connection failed: {e}")

            # Start reconnection if enabled
            if self._config.enabled and not self._should_stop:
                self._start_reconnect()

            return False

    async def disconnect(self) -> None:
        """Disconnect and stop reconnection"""
        self._should_stop = True

        # Cancel any ongoing reconnection
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass

        if self._state in (ConnectionState.CONNECTED, ConnectionState.RECONNECTING):
            try:
                await self._disconnect_fn()
            except Exception as e:
                logger.error(f"[{self.channel_id}] Disconnect error: {e}")

        self._metrics.disconnected_at = datetime.now(UTC)
        await self._set_state(ConnectionState.STOPPED)
        logger.info(f"[{self.channel_id}] Disconnected")

    def _start_reconnect(self) -> None:
        """Start reconnection task"""
        if self._reconnect_task and not self._reconnect_task.done():
            return  # Already reconnecting

        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff"""
        await self._set_state(ConnectionState.RECONNECTING)

        while not self._should_stop and self._current_attempt < self._config.max_attempts:
            self._current_attempt += 1

            # Calculate delay
            delay = self._calculate_delay()
            logger.info(
                f"[{self.channel_id}] Reconnect attempt {self._current_attempt}/"
                f"{self._config.max_attempts} in {delay:.1f}s"
            )

            await asyncio.sleep(delay)

            if self._should_stop:
                break

            try:
                await self._connect_fn()
                await self._set_state(ConnectionState.CONNECTED)
                self._metrics.connected_at = datetime.now(UTC)
                self._metrics.disconnected_at = None
                self._metrics.reconnect_count += 1
                self._metrics.last_reconnect_at = datetime.now(UTC)
                self._current_attempt = 0
                logger.info(f"[{self.channel_id}] Reconnected successfully")
                return

            except Exception as e:
                self._metrics.record_error(str(e))
                logger.warning(f"[{self.channel_id}] Reconnect failed: {e}")

        if not self._should_stop:
            logger.error(
                f"[{self.channel_id}] Max reconnect attempts reached "
                f"({self._config.max_attempts})"
            )
            await self._set_state(ConnectionState.ERROR)

    def _calculate_delay(self) -> float:
        """Calculate reconnection delay"""
        if self._config.exponential_backoff:
            delay = min(
                self._config.base_delay * (2 ** (self._current_attempt - 1)), self._config.max_delay
            )
        else:
            delay = self._config.base_delay

        # Add jitter (up to 25% variation)
        if self._config.jitter:
            import random

            jitter = delay * 0.25 * random.random()
            delay += jitter

        return delay

    def handle_connection_error(self, error: Exception) -> None:
        """
        Handle connection error (called externally)

        This should be called when the underlying connection encounters an error.
        """
        self._metrics.record_error(str(error))

        if self._state == ConnectionState.CONNECTED and self._config.enabled:
            logger.warning(f"[{self.channel_id}] Connection error: {error}")
            self._start_reconnect()


class HealthChecker:
    """
    Health checker for channels
    """

    def __init__(
        self,
        channel_id: str,
        check_fn: Callable[[], Awaitable[bool]],
        interval: float = 30.0,  # Check every 30 seconds
        timeout: float = 10.0,  # Check timeout
    ):
        """
        Initialize health checker

        Args:
            channel_id: Channel identifier
            check_fn: Async function that returns True if healthy
            interval: Check interval in seconds
            timeout: Check timeout in seconds
        """
        self.channel_id = channel_id
        self._check_fn = check_fn
        self._interval = interval
        self._timeout = timeout

        self._task: asyncio.Task | None = None
        self._healthy = False
        self._last_check: datetime | None = None
        self._consecutive_failures = 0
        self._on_unhealthy: Callable[[], Awaitable[None]] | None = None

    @property
    def is_healthy(self) -> bool:
        """Check if channel is healthy"""
        return self._healthy

    @property
    def last_check(self) -> datetime | None:
        """Get last check time"""
        return self._last_check

    def set_unhealthy_callback(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Set callback for when channel becomes unhealthy"""
        self._on_unhealthy = callback

    def start(self) -> None:
        """Start health checking"""
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._check_loop())
        logger.info(f"[{self.channel_id}] Health checker started")

    def stop(self) -> None:
        """Stop health checking"""
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info(f"[{self.channel_id}] Health checker stopped")

    async def _check_loop(self) -> None:
        """Health check loop"""
        while True:
            try:
                await asyncio.sleep(self._interval)
                await self._perform_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{self.channel_id}] Health check error: {e}")

    async def _perform_check(self) -> None:
        """Perform single health check"""
        self._last_check = datetime.now(UTC)

        try:
            healthy = await asyncio.wait_for(self._check_fn(), timeout=self._timeout)

            if healthy:
                self._healthy = True
                self._consecutive_failures = 0
            else:
                await self._handle_failure("Check returned false")

        except TimeoutError:
            await self._handle_failure("Check timed out")
        except Exception as e:
            await self._handle_failure(str(e))

    async def _handle_failure(self, reason: str) -> None:
        """Handle health check failure"""
        self._consecutive_failures += 1
        logger.warning(
            f"[{self.channel_id}] Health check failed ({self._consecutive_failures}): {reason}"
        )

        if self._consecutive_failures >= 3:
            self._healthy = False
            if self._on_unhealthy:
                await self._on_unhealthy()

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "healthy": self._healthy,
            "last_check": self._last_check.isoformat() if self._last_check else None,
            "consecutive_failures": self._consecutive_failures,
            "interval_seconds": self._interval,
            "timeout_seconds": self._timeout,
        }
