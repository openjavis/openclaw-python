"""Unit tests for RPC client"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openclaw.gateway.rpc_client import GatewayRPCClient, GatewayRPCError


@pytest.mark.asyncio
async def test_rpc_client_initialization():
    """Test RPC client initialization"""
    client = GatewayRPCClient()
    assert client.url == "ws://localhost:18789"
    assert client._request_id == 0


@pytest.mark.asyncio
async def test_rpc_client_with_config():
    """Test RPC client initialization with config"""
    from openclaw.config.schema import ClawdbotConfig, GatewayConfig
    
    config = ClawdbotConfig()
    config.gateway = GatewayConfig(port=9999)
    
    client = GatewayRPCClient(config=config)
    assert client.url == "ws://localhost:9999"


@pytest.mark.asyncio
async def test_next_id():
    """Test request ID generation"""
    client = GatewayRPCClient()
    
    id1 = client._next_id()
    id2 = client._next_id()
    id3 = client._next_id()
    
    assert id1 == 1
    assert id2 == 2
    assert id3 == 3


@pytest.mark.asyncio
async def test_call_success():
    """Test successful RPC call"""
    client = GatewayRPCClient()
    
    mock_response = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"status": "ok"}
    }
    
    with patch("websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(return_value='{"jsonrpc": "2.0", "id": 1, "result": {"status": "ok"}}')
        mock_connect.return_value.__aenter__.return_value = mock_ws
        
        result = await client.call("test.method", {"param": "value"})
        
        assert result == {"status": "ok"}
        mock_ws.send.assert_called()


@pytest.mark.asyncio
async def test_call_error():
    """Test RPC call with error response"""
    client = GatewayRPCClient()
    
    with patch("websockets.connect") as mock_connect:
        mock_ws = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.recv = AsyncMock(return_value='{"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}')
        mock_connect.return_value.__aenter__.return_value = mock_ws
        
        with pytest.raises(GatewayRPCError, match="Method not found"):
            await client.call("unknown.method")
