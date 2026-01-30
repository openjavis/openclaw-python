"""
Tests for enhanced channel system
"""

import asyncio
from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from openclaw.channels.base import (
    ChannelCapabilities,
    ChannelPlugin,
    InboundMessage,
    OutboundMessage,
)
from openclaw.channels.connection import (
    ConnectionManager,
    ConnectionMetrics,
    ConnectionState,
    HealthChecker,
    ReconnectConfig,
)


class TestConnectionState:
    """Test ConnectionState enum"""

    def test_state_values(self):
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.RECONNECTING.value == "reconnecting"
        assert ConnectionState.ERROR.value == "error"
        assert ConnectionState.STOPPED.value == "stopped"


class TestConnectionMetrics:
    """Test ConnectionMetrics class"""

    def test_initial_metrics(self):
        metrics = ConnectionMetrics()
        assert metrics.messages_sent == 0
        assert metrics.messages_received == 0
        assert metrics.errors_count == 0

    def test_record_message_sent(self):
        metrics = ConnectionMetrics()
        metrics.record_message_sent()
        assert metrics.messages_sent == 1

    def test_record_message_received(self):
        metrics = ConnectionMetrics()
        metrics.record_message_received()
        assert metrics.messages_received == 1

    def test_record_error(self):
        metrics = ConnectionMetrics()
        metrics.record_error("Test error")

        assert metrics.errors_count == 1
        assert metrics.last_error == "Test error"
        assert metrics.last_error_at is not None

    def test_record_heartbeat(self):
        metrics = ConnectionMetrics()
        metrics.record_heartbeat()
        assert metrics.last_heartbeat is not None

    def test_uptime(self):
        metrics = ConnectionMetrics()
        metrics.connected_at = datetime.now(UTC)

        uptime = metrics.get_uptime_seconds()
        assert uptime is not None
        assert uptime >= 0

    def test_to_dict(self):
        metrics = ConnectionMetrics()
        metrics.record_message_sent()

        data = metrics.to_dict()
        assert data["messages_sent"] == 1
        assert "uptime_seconds" in data


class TestReconnectConfig:
    """Test ReconnectConfig class"""

    def test_default_config(self):
        config = ReconnectConfig()
        assert config.enabled is True
        assert config.max_attempts == 5
        assert config.base_delay == 1.0

    def test_custom_config(self):
        config = ReconnectConfig(enabled=False, max_attempts=10, base_delay=2.0)
        assert config.enabled is False
        assert config.max_attempts == 10


class TestConnectionManager:
    """Test ConnectionManager class"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        connect_fn = AsyncMock()
        disconnect_fn = AsyncMock()

        manager = ConnectionManager(
            channel_id="test", connect_fn=connect_fn, disconnect_fn=disconnect_fn
        )

        result = await manager.connect()

        assert result is True
        assert manager.state == ConnectionState.CONNECTED
        assert manager.is_connected is True
        connect_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        connect_fn = AsyncMock(side_effect=Exception("Connection failed"))
        disconnect_fn = AsyncMock()

        manager = ConnectionManager(
            channel_id="test",
            connect_fn=connect_fn,
            disconnect_fn=disconnect_fn,
            reconnect_config=ReconnectConfig(enabled=False),
        )

        result = await manager.connect()

        assert result is False
        assert manager.state == ConnectionState.ERROR

    @pytest.mark.asyncio
    async def test_disconnect(self):
        connect_fn = AsyncMock()
        disconnect_fn = AsyncMock()

        manager = ConnectionManager(
            channel_id="test", connect_fn=connect_fn, disconnect_fn=disconnect_fn
        )

        await manager.connect()
        await manager.disconnect()

        assert manager.state == ConnectionState.STOPPED
        disconnect_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_state_callback(self):
        connect_fn = AsyncMock()
        disconnect_fn = AsyncMock()
        callback = AsyncMock()

        manager = ConnectionManager(
            channel_id="test", connect_fn=connect_fn, disconnect_fn=disconnect_fn
        )
        manager.add_state_callback(callback)

        await manager.connect()

        # Should have been called for CONNECTING and CONNECTED
        assert callback.call_count >= 2

    def test_metrics(self):
        connect_fn = AsyncMock()
        disconnect_fn = AsyncMock()

        manager = ConnectionManager(
            channel_id="test", connect_fn=connect_fn, disconnect_fn=disconnect_fn
        )

        metrics = manager.metrics
        assert isinstance(metrics, ConnectionMetrics)

    def test_handle_connection_error(self):
        connect_fn = AsyncMock()
        disconnect_fn = AsyncMock()

        manager = ConnectionManager(
            channel_id="test",
            connect_fn=connect_fn,
            disconnect_fn=disconnect_fn,
            reconnect_config=ReconnectConfig(enabled=False),
        )

        manager.handle_connection_error(Exception("Test error"))

        assert manager.metrics.errors_count == 1


class TestHealthChecker:
    """Test HealthChecker class"""

    @pytest.mark.asyncio
    async def test_health_checker_start_stop(self):
        check_fn = AsyncMock(return_value=True)

        checker = HealthChecker(channel_id="test", check_fn=check_fn, interval=0.1)

        checker.start()
        await asyncio.sleep(0.2)
        checker.stop()

        # Should have performed at least one check
        assert check_fn.called

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        check_fn = AsyncMock(return_value=True)

        checker = HealthChecker(channel_id="test", check_fn=check_fn, interval=0.1)

        checker.start()
        await asyncio.sleep(0.15)
        checker.stop()

        assert checker.is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        check_fn = AsyncMock(return_value=False)

        checker = HealthChecker(channel_id="test", check_fn=check_fn, interval=0.05)

        checker.start()
        await asyncio.sleep(0.2)  # Wait for multiple checks
        checker.stop()

        # After consecutive failures, should be unhealthy
        assert checker._consecutive_failures >= 1

    def test_to_dict(self):
        check_fn = AsyncMock()

        checker = HealthChecker(channel_id="test", check_fn=check_fn)

        data = checker.to_dict()
        assert "healthy" in data
        assert "interval_seconds" in data


class MockChannel(ChannelPlugin):
    """Mock channel for testing"""

    def __init__(self):
        super().__init__()
        self.id = "mock"
        self.label = "Mock Channel"
        self.start_called = False
        self.stop_called = False

    async def start(self, config):
        self.start_called = True
        self._running = True

    async def stop(self):
        self.stop_called = True
        self._running = False

    async def send_text(self, target, text, reply_to=None):
        return "msg-123"


class TestChannelPlugin:
    """Test enhanced ChannelPlugin class"""

    def test_channel_creation(self):
        channel = MockChannel()
        assert channel.id == "mock"
        assert channel.is_running() is False

    @pytest.mark.asyncio
    async def test_channel_start_stop(self):
        channel = MockChannel()

        await channel.start({})
        assert channel.is_running() is True

        await channel.stop()
        assert channel.is_running() is False

    @pytest.mark.asyncio
    async def test_channel_send(self):
        channel = MockChannel()
        await channel.start({})

        msg_id = await channel.send_text("target", "Hello")
        assert msg_id == "msg-123"

    def test_channel_to_dict(self):
        channel = MockChannel()
        data = channel.to_dict()

        assert data["id"] == "mock"
        assert data["label"] == "Mock Channel"
        assert "capabilities" in data
        assert "running" in data
        assert "connected" in data
        assert "healthy" in data
        assert "state" in data

    def test_capabilities(self):
        caps = ChannelCapabilities(
            chat_types=["direct", "group"], supports_media=True, supports_reactions=True
        )

        assert "direct" in caps.chat_types
        assert caps.supports_media is True


class TestInboundMessage:
    """Test InboundMessage class"""

    def test_message_creation(self):
        msg = InboundMessage(
            channel_id="telegram",
            message_id="123",
            sender_id="user1",
            sender_name="User One",
            chat_id="chat1",
            chat_type="direct",
            text="Hello",
            timestamp="2026-01-28T12:00:00Z",
        )

        assert msg.channel_id == "telegram"
        assert msg.text == "Hello"
        assert msg.chat_type == "direct"

    def test_message_with_metadata(self):
        msg = InboundMessage(
            channel_id="telegram",
            message_id="123",
            sender_id="user1",
            sender_name="User One",
            chat_id="chat1",
            chat_type="direct",
            text="Hello",
            timestamp="2026-01-28T12:00:00Z",
            reply_to="122",
            metadata={"username": "user_one"},
        )

        assert msg.reply_to == "122"
        assert msg.metadata["username"] == "user_one"


class TestOutboundMessage:
    """Test OutboundMessage class"""

    def test_message_creation(self):
        msg = OutboundMessage(channel_id="telegram", target="user1", text="Hello back")

        assert msg.channel_id == "telegram"
        assert msg.text == "Hello back"
