"""End-to-end integration tests for gateway"""

import asyncio
import pytest
import websockets
import json

from openclaw.gateway.bootstrap import GatewayBootstrap


@pytest.mark.asyncio
@pytest.mark.integration
async def test_gateway_startup():
    """Test complete gateway startup sequence"""
    bootstrap = GatewayBootstrap()
    
    try:
        result = await bootstrap.bootstrap()
        
        assert result["steps_completed"] >= 15
        assert bootstrap.config is not None
        assert bootstrap.server is not None
        
    finally:
        await bootstrap.shutdown()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_gateway_websocket_connect():
    """Test WebSocket connection to gateway"""
    bootstrap = GatewayBootstrap()
    
    try:
        await bootstrap.bootstrap()
        
        # Give server time to start
        await asyncio.sleep(1)
        
        port = bootstrap.config.gateway.port if bootstrap.config.gateway else 18789
        
        # Test connection
        async with websockets.connect(f"ws://localhost:{port}") as ws:
            # Send connect handshake
            connect_req = {
                "jsonrpc": "2.0",
                "method": "connect",
                "params": {
                    "minProtocol": 1,
                    "maxProtocol": 1,
                    "client": {
                        "name": "test-client",
                        "version": "1.0.0",
                        "platform": "test"
                    }
                },
                "id": 1
            }
            
            await ws.send(json.dumps(connect_req))
            response_data = await ws.recv()
            response = json.loads(response_data)
            
            assert "result" in response
            assert response["result"]["protocol"] == 1
            
    finally:
        await bootstrap.shutdown()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_gateway_agent_call():
    """Test making an agent call through gateway"""
    bootstrap = GatewayBootstrap()
    
    try:
        await bootstrap.bootstrap()
        await asyncio.sleep(1)
        
        port = bootstrap.config.gateway.port if bootstrap.config.gateway else 18789
        
        async with websockets.connect(f"ws://localhost:{port}") as ws:
            # Connect handshake
            connect_req = {
                "jsonrpc": "2.0",
                "method": "connect",
                "params": {
                    "minProtocol": 1,
                    "maxProtocol": 1,
                    "client": {"name": "test", "version": "1.0", "platform": "test"}
                },
                "id": 1
            }
            await ws.send(json.dumps(connect_req))
            await ws.recv()  # Consume connect response
            
            # Agent call
            agent_req = {
                "jsonrpc": "2.0",
                "method": "agent",
                "params": {
                    "message": "Hello, test message",
                    "sessionId": "test-session"
                },
                "id": 2
            }
            await ws.send(json.dumps(agent_req))
            
            response_data = await ws.recv()
            response = json.loads(response_data)
            
            # Should either succeed or fail with a clear error
            assert "result" in response or "error" in response
            
            if "result" in response:
                assert "response" in response["result"]
            
    finally:
        await bootstrap.shutdown()
