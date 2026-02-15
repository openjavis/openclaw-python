#!/usr/bin/env python3
"""Test script for unified HTTP+WebSocket server"""

import asyncio
import aiohttp
from openclaw.config import load_config
from openclaw.gateway.server import GatewayServer


async def test_server():
    """Start test server"""
    # Load config
    config = load_config()
    
    # Create server
    server = GatewayServer(
        config=config,
        agent_runtime=None,  # Minimal test
        session_manager=None,
        auto_discover_channels=False
    )
    
    print("✓ Server instance created")
    print(f"✓ Port: {config.gateway.port}")
    
    # Start server
    try:
        await server.start(start_channels=False)
    except KeyboardInterrupt:
        print("\n✓ Server stopped")


if __name__ == "__main__":
    print("🧪 Testing Unified Gateway Server")
    print("=" * 50)
    try:
        asyncio.run(test_server())
    except KeyboardInterrupt:
        print("\n✓ Test interrupted")
