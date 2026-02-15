"""
Gateway API Method Implementations

Core methods for Gateway WebSocket API.
"""
from __future__ import annotations


import logging
from typing import Any

from .chat import CHAT_METHODS

logger = logging.getLogger(__name__)


# =============================================================================
# Connection Methods
# =============================================================================


class ConnectMethod:
    """
    Connect method - establish WebSocket connection

    This is the first method called when a client connects.
    """

    name = "connect"
    description = "Establish WebSocket connection and negotiate protocol"
    category = "connection"

    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute connect handshake

        Args:
            connection: GatewayConnection
            params: {
                "maxProtocol": int,
                "client": {
                    "name": str,
                    "version": str,
                    "platform": str
                }
            }

        Returns:
            Hello response with server info
        """
        max_protocol = params.get("maxProtocol", 1)
        client_info = params.get("client", {})

        # Negotiate protocol
        negotiated_protocol = min(max_protocol, 1)

        # Store client info
        connection.client_info = client_info
        connection.protocol_version = negotiated_protocol
        connection.authenticated = True

        logger.info(f"Client connected: {client_info.get('name', 'unknown')}")

        # Return hello response
        return {
            "protocol": negotiated_protocol,
            "server": {"name": "openclaw-python", "version": "0.6.0", "platform": "python"},
            "features": {
                "agent": True,
                "chat": True,
                "sessions": True,
                "channels": True,
                "tools": True,
            },
            "snapshot": {
                "sessions": [],
                "channels": [],
                "agents": [],
            },
        }

    def get_schema(self) -> dict[str, Any]:
        """Get parameter schema"""
        return {
            "type": "object",
            "properties": {
                "maxProtocol": {"type": "integer"},
                "client": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "platform": {"type": "string"},
                    },
                },
            },
            "required": ["maxProtocol", "client"],
        }


class PingMethod:
    """Ping method - check connection health"""

    name = "ping"
    description = "Ping server to check connection health"
    category = "connection"

    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Execute ping"""
        return {"pong": True, "timestamp": params.get("timestamp")}

    def get_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"timestamp": {"type": "integer"}}}


# =============================================================================
# Agent Methods
# =============================================================================


class AgentMethod:
    """
    Agent method - send message to agent

    This is one of the TWO methods that directly call Agent Runtime.
    """

    name = "agent"
    description = "Send message to agent and receive streaming response"
    category = "agent"

    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute agent turn

        Args:
            connection: GatewayConnection
            params: {
                "message": str,
                "sessionId": str,
                "tools": list[str] | None,
                "maxTokens": int | None
            }

        Returns:
            Streaming events via connection.send_event()
        """
        message = params.get("message", "")
        session_id = params.get("sessionId")

        if not message:
            raise ValueError("Message is required")

        logger.info(f"Agent request: session={session_id}, message={message[:50]}...")

        # This would integrate with AgentRuntime
        # For now, return placeholder
        return {
            "sessionId": session_id,
            "status": "streaming",
            "message": "Agent response would stream here",
        }

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "sessionId": {"type": "string"},
                "tools": {"type": "array", "items": {"type": "string"}},
                "maxTokens": {"type": "integer"},
            },
            "required": ["message"],
        }


# =============================================================================
# System Methods
# =============================================================================


class HealthMethod:
    """Health method - get server health status"""

    name = "health"
    description = "Get Gateway server health status"
    category = "system"

    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Execute health check"""
        # Access gateway from connection if available
        gateway = getattr(connection, "gateway", None)

        health = {
            "status": "healthy",
            "uptime": 0,  # Would need to track this
            "connections": 0,
        }

        if gateway and hasattr(gateway, "channel_manager"):
            channel_status = gateway.channel_manager.get_all_status()
            health["channels"] = {
                "total": channel_status.get("total", 0),
                "running": channel_status.get("running_count", 0),
            }

        return health

    def get_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}


# =============================================================================
# Channel Methods
# =============================================================================


class ChannelsListMethod:
    """List all channels"""

    name = "channels.list"
    description = "List all registered channels and their status"
    category = "channels"

    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """List channels"""
        gateway = getattr(connection, "gateway", None)

        if not gateway or not hasattr(gateway, "channel_manager"):
            return {"channels": []}

        return gateway.channel_manager.get_all_status()

    def get_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}


class ChannelsStartMethod:
    """Start a channel"""

    name = "channels.start"
    description = "Start a specific channel"
    category = "channels"

    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Start channel"""
        channel_id = params.get("channelId")
        if not channel_id:
            raise ValueError("channelId is required")

        gateway = getattr(connection, "gateway", None)
        if not gateway or not hasattr(gateway, "channel_manager"):
            raise RuntimeError("ChannelManager not available")

        success = await gateway.channel_manager.start_channel(channel_id)

        return {
            "channelId": channel_id,
            "success": success,
            "status": gateway.channel_manager.get_status(channel_id),
        }

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"channelId": {"type": "string"}},
            "required": ["channelId"],
        }


class ChannelsStopMethod:
    """Stop a channel"""

    name = "channels.stop"
    description = "Stop a specific channel"
    category = "channels"

    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Stop channel"""
        channel_id = params.get("channelId")
        if not channel_id:
            raise ValueError("channelId is required")

        gateway = getattr(connection, "gateway", None)
        if not gateway or not hasattr(gateway, "channel_manager"):
            raise RuntimeError("ChannelManager not available")

        success = await gateway.channel_manager.stop_channel(channel_id)

        return {"channelId": channel_id, "success": success}

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"channelId": {"type": "string"}},
            "required": ["channelId"],
        }


# =============================================================================
# Method Registry
# =============================================================================

# All available methods
ALL_METHODS = [
    ConnectMethod(),
    PingMethod(),
    AgentMethod(),
    HealthMethod(),
    ChannelsListMethod(),
    ChannelsStartMethod(),
    ChannelsStopMethod(),
    *CHAT_METHODS,  # Add all chat methods
]

# Method lookup by name
METHOD_REGISTRY = {method.name: method for method in ALL_METHODS}


def get_method_handler(method_name: str):
    """Get method handler by name"""
    return METHOD_REGISTRY.get(method_name)
