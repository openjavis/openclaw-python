"""
Tests for WebSocket streaming
"""

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from openclaw.api.websocket import (
    ConnectionState,
    MessageType,
    WebSocketConnection,
    WebSocketManager,
    WebSocketMessage,
)


class TestMessageType:
    """Test MessageType enum"""

    def test_message_types(self):
        """Test enum values"""
        assert MessageType.PING == "ping"
        assert MessageType.REQUEST == "request"
        assert MessageType.RESPONSE == "response"
        assert MessageType.STREAM_START == "stream_start"


class TestWebSocketMessage:
    """Test WebSocketMessage class"""

    def test_init(self):
        """Test creating a message"""
        msg = WebSocketMessage(type=MessageType.REQUEST, data={"test": "data"})

        assert msg.type == MessageType.REQUEST
        assert msg.data == {"test": "data"}
        assert msg.request_id is not None

    def test_to_dict(self):
        """Test converting to dict"""
        msg = WebSocketMessage(type=MessageType.RESPONSE, data="test", request_id="123")

        data = msg.to_dict()

        assert data["type"] == "response"
        assert data["data"] == "test"
        assert data["request_id"] == "123"

    def test_to_json(self):
        """Test converting to JSON"""
        msg = WebSocketMessage(type=MessageType.PING)

        json_str = msg.to_json()

        assert isinstance(json_str, str)
        assert "ping" in json_str

    def test_from_dict(self):
        """Test creating from dict"""
        data = {"type": "request", "data": {"key": "value"}, "request_id": "456"}

        msg = WebSocketMessage.from_dict(data)

        assert msg.type == MessageType.REQUEST
        assert msg.data == {"key": "value"}
        assert msg.request_id == "456"

    def test_round_trip(self):
        """Test JSON round trip"""
        msg1 = WebSocketMessage(type=MessageType.RESPONSE, data="test")

        json_str = msg1.to_json()
        msg2 = WebSocketMessage.from_json(json_str)

        assert msg2.type == msg1.type
        assert msg2.data == msg1.data


class TestConnectionState:
    """Test ConnectionState enum"""

    def test_states(self):
        """Test enum values"""
        assert ConnectionState.CONNECTING == "connecting"
        assert ConnectionState.CONNECTED == "connected"
        assert ConnectionState.DISCONNECTED == "disconnected"


class TestWebSocketConnection:
    """Test WebSocketConnection class"""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.close = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_json = AsyncMock()
        return ws

    def test_init(self, mock_websocket):
        """Test initializing connection"""
        conn = WebSocketConnection(mock_websocket)

        assert conn.websocket == mock_websocket
        assert conn.state == ConnectionState.CONNECTING
        assert conn.connection_id is not None

    @pytest.mark.asyncio
    async def test_accept(self, mock_websocket):
        """Test accepting connection"""
        conn = WebSocketConnection(mock_websocket)

        await conn.accept()

        assert conn.state == ConnectionState.CONNECTED
        assert conn.connected_at is not None
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, mock_websocket):
        """Test closing connection"""
        conn = WebSocketConnection(mock_websocket)
        await conn.accept()

        await conn.close()

        assert conn.state == ConnectionState.DISCONNECTED
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message(self, mock_websocket):
        """Test sending message"""
        conn = WebSocketConnection(mock_websocket)
        await conn.accept()

        msg = WebSocketMessage(type=MessageType.RESPONSE, data="test")
        await conn.send_message(msg)

        # Give time for send loop to process
        await asyncio.sleep(0.1)

        assert mock_websocket.send_json.called

    def test_is_alive(self, mock_websocket):
        """Test checking if connection is alive"""
        conn = WebSocketConnection(mock_websocket)

        assert not conn.is_alive()  # Not connected yet

        conn.state = ConnectionState.CONNECTED
        assert conn.is_alive()

        conn.state = ConnectionState.DISCONNECTED
        assert not conn.is_alive()

    def test_get_uptime_seconds(self, mock_websocket):
        """Test getting uptime"""
        conn = WebSocketConnection(mock_websocket)

        # No uptime before connection
        assert conn.get_uptime_seconds() == 0.0

        # Set connection time
        conn.connected_at = datetime.now(UTC) - timedelta(seconds=10)
        uptime = conn.get_uptime_seconds()

        assert uptime >= 10.0


class TestWebSocketManager:
    """Test WebSocketManager class"""

    @pytest.fixture
    def mock_connection(self):
        """Create mock connection"""
        conn = Mock(spec=WebSocketConnection)
        conn.connection_id = "test-123"
        conn.is_alive = Mock(return_value=True)
        conn.send_message = AsyncMock()
        conn.close = AsyncMock()
        conn.last_activity = datetime.now(UTC)
        return conn

    def test_init(self):
        """Test initializing manager"""
        manager = WebSocketManager()

        assert len(manager.connections) == 0

    def test_add_connection(self, mock_connection):
        """Test adding connection"""
        manager = WebSocketManager()

        manager.add_connection(mock_connection)

        assert len(manager.connections) == 1
        assert "test-123" in manager.connections

    def test_remove_connection(self, mock_connection):
        """Test removing connection"""
        manager = WebSocketManager()
        manager.add_connection(mock_connection)

        manager.remove_connection("test-123")

        assert len(manager.connections) == 0

    def test_get_connection(self, mock_connection):
        """Test getting connection"""
        manager = WebSocketManager()
        manager.add_connection(mock_connection)

        conn = manager.get_connection("test-123")

        assert conn == mock_connection

    def test_get_connection_not_found(self):
        """Test getting non-existent connection"""
        manager = WebSocketManager()

        conn = manager.get_connection("nonexistent")

        assert conn is None

    @pytest.mark.asyncio
    async def test_broadcast(self, mock_connection):
        """Test broadcasting message"""
        manager = WebSocketManager()
        manager.add_connection(mock_connection)

        msg = WebSocketMessage(type=MessageType.RESPONSE, data="broadcast")
        await manager.broadcast(msg)

        mock_connection.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_exclude(self, mock_connection):
        """Test broadcasting with exclusions"""
        manager = WebSocketManager()
        manager.add_connection(mock_connection)

        msg = WebSocketMessage(type=MessageType.RESPONSE)
        await manager.broadcast(msg, exclude=["test-123"])

        mock_connection.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_inactive(self, mock_connection):
        """Test cleaning up inactive connections"""
        manager = WebSocketManager()
        manager.add_connection(mock_connection)

        # Make connection inactive
        mock_connection.last_activity = datetime.now(UTC) - timedelta(seconds=400)

        cleaned = await manager.cleanup_inactive(timeout_seconds=300)

        assert cleaned == 1
        assert len(manager.connections) == 0

    @pytest.mark.asyncio
    async def test_cleanup_dead_connections(self, mock_connection):
        """Test cleaning up dead connections"""
        manager = WebSocketManager()
        manager.add_connection(mock_connection)

        # Make connection dead
        mock_connection.is_alive = Mock(return_value=False)

        cleaned = await manager.cleanup_inactive()

        assert cleaned == 1

    def test_get_stats(self, mock_connection):
        """Test getting statistics"""
        manager = WebSocketManager()
        manager.add_connection(mock_connection)

        stats = manager.get_stats()

        assert stats["total_connections"] == 1
        assert stats["active_connections"] == 1
        assert stats["inactive_connections"] == 0
