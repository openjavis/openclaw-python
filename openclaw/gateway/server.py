"""Gateway WebSocket server implementation

This is the main Gateway Server that:
1. Manages channel plugins via ChannelManager
2. Provides WebSocket API for external clients
3. Broadcasts events to connected clients (Observer Pattern)

Architecture:
    Gateway Server
        ├── ChannelManager (manages channel plugins)
        │       ├── Telegram Channel
        │       ├── Discord Channel
        │       └── ...
        │
        ├── WebSocket Server (for external clients)
        │       ├── Control UI
        │       ├── CLI tools
        │       └── Mobile apps
        │
        └── Event Broadcasting (Observer Pattern)
                └── Receives events from Agent Runtime
                    and broadcasts to all WebSocket clients
"""

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from ..config import ClawdbotConfig
from ..events import Event
from .channel_manager import ChannelManager, discover_channel_plugins
from .handlers import get_method_handler
from .protocol import ErrorShape, EventFrame, RequestFrame, ResponseFrame
from .protocol.frames import ConnectRequest, HelloResponse

logger = logging.getLogger(__name__)


class GatewayConnection:
    """Represents a single WebSocket connection"""

    def __init__(self, websocket: WebSocketServerProtocol, config: ClawdbotConfig):
        self.websocket = websocket
        self.config = config
        self.authenticated = False
        self.client_info: dict[str, Any] | None = None
        self.protocol_version = 1

    async def send_response(
        self, request_id: str, payload: Any = None, error: ErrorShape | None = None
    ) -> None:
        """Send response frame"""
        response = ResponseFrame(id=request_id, ok=error is None, payload=payload, error=error)
        await self.websocket.send(response.model_dump_json())

    async def send_event(self, event: str, payload: Any = None) -> None:
        """Send event frame"""
        event_frame = EventFrame(event=event, payload=payload)
        await self.websocket.send(event_frame.model_dump_json())

    async def handle_message(self, message: str) -> None:
        """Handle incoming message"""
        try:
            data = json.loads(message)
            frame_type = data.get("type")

            if frame_type == "req":
                request = RequestFrame(**data)
                await self.handle_request(request)
            else:
                logger.warning(f"Unknown frame type: {frame_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def handle_request(self, request: RequestFrame) -> None:
        """Handle request frame"""
        try:
            # Special handling for connect method
            if request.method == "connect":
                await self.handle_connect(request)
                return

            # Check authentication for other methods
            if not self.authenticated and request.method != "health":
                await self.send_response(
                    request.id,
                    error=ErrorShape(
                        code="AUTH_REQUIRED",
                        message="Authentication required. Send 'connect' request first.",
                    ),
                )
                return

            # Get method handler
            handler = get_method_handler(request.method)
            if handler is None:
                await self.send_response(
                    request.id,
                    error=ErrorShape(
                        code="METHOD_NOT_FOUND", message=f"Method '{request.method}' not found"
                    ),
                )
                return

            # Execute handler
            result = await handler(self, request.params or {})
            await self.send_response(request.id, payload=result)

        except Exception as e:
            logger.error(f"Error handling request {request.method}: {e}", exc_info=True)
            await self.send_response(
                request.id, error=ErrorShape(code="INTERNAL_ERROR", message=str(e))
            )

    async def handle_connect(self, request: RequestFrame) -> None:
        """Handle connection handshake"""
        try:
            connect_req = ConnectRequest(**(request.params or {}))

            # Negotiate protocol version
            negotiated_protocol = min(connect_req.maxProtocol, 1)

            self.client_info = connect_req.client
            self.protocol_version = negotiated_protocol
            self.authenticated = True

            # Send hello response
            hello = HelloResponse(
                protocol=negotiated_protocol,
                server={"name": "openclaw-python", "version": "0.1.0", "platform": "python"},
                features={
                    "agent": True,
                    "chat": True,
                    "sessions": True,
                    "channels": True,
                    "tools": True,
                },
                snapshot={"sessions": [], "channels": [], "agents": []},
            )

            await self.send_response(request.id, payload=hello.model_dump())
            logger.info(f"Client connected: {self.client_info}")

        except Exception as e:
            logger.error(f"Connect handshake failed: {e}", exc_info=True)
            await self.send_response(
                request.id, error=ErrorShape(code="HANDSHAKE_FAILED", message=str(e))
            )


class GatewayServer:
    """
    Gateway WebSocket server

    This is the main entry point for OpenClaw Gateway, providing:
    1. ChannelManager - Manages all channel plugins (Telegram, Discord, etc.)
    2. WebSocket API - Serves external clients (UI, CLI, mobile)
    3. Event Broadcasting - Broadcasts Agent events to all clients

    Architecture follows TypeScript OpenClaw design:
    - Gateway contains ChannelManager
    - Channels are plugins inside Gateway (not external clients)
    - Gateway observes Agent Runtime for events
    - WebSocket is for external clients only

    Example:
        config = ClawdbotConfig(...)
        gateway = GatewayServer(config, agent_runtime, session_manager)

        # Register channels
        gateway.channel_manager.register("telegram", EnhancedTelegramChannel)
        gateway.channel_manager.configure("telegram", {"bot_token": "..."})

        # Start gateway (starts WebSocket + all enabled channels)
        await gateway.start()
    """

    def __init__(
        self,
        config: ClawdbotConfig,
        agent_runtime=None,
        session_manager=None,
        tools=None,
        system_prompt: str | None = None,
        auto_discover_channels: bool = False,
    ):
        """
        Initialize Gateway Server

        Args:
            config: Gateway configuration
            agent_runtime: AgentRuntime instance (shared with channels)
            session_manager: SessionManager for managing sessions
            tools: List of tools available to the agent
            system_prompt: Optional system prompt (skills, capabilities)
            auto_discover_channels: If True, auto-discover and register channel plugins
        """
        self.config = config
        self.connections: set[GatewayConnection] = set()
        self.running = False
        self.agent_runtime = agent_runtime
        self.session_manager = session_manager
        self.tools = tools or []
        self.system_prompt = system_prompt

        # Create ChannelManager
        self.channel_manager = ChannelManager(
            default_runtime=agent_runtime,
            session_manager=session_manager,
            tools=self.tools,
            system_prompt=self.system_prompt,
        )

        # Register as observer if agent_runtime provided
        if agent_runtime:
            agent_runtime.add_event_listener(self.on_agent_event)
            logger.info("Gateway registered as Agent Runtime observer")

        # Listen for channel events to broadcast
        self.channel_manager.add_event_listener(self._on_channel_event)

        # Auto-discover channel plugins if requested
        if auto_discover_channels:
            self._discover_and_register_channels()

        logger.info("GatewayServer initialized with ChannelManager")

    def _discover_and_register_channels(self) -> None:
        """Discover and register available channel plugins"""
        plugins = discover_channel_plugins()
        for channel_id, channel_class in plugins.items():
            self.channel_manager.register(channel_id, channel_class)
        logger.info(f"Auto-discovered {len(plugins)} channel plugins")

    async def _on_channel_event(
        self,
        event_type: str,
        channel_id: str,
        data: dict[str, Any],
    ) -> None:
        """
        Handle channel manager events

        Broadcasts channel lifecycle events to WebSocket clients.
        """
        await self.broadcast_event(
            "channel",
            {
                "event": event_type,
                "channel_id": channel_id,
                "data": data,
            },
        )

    async def on_agent_event(self, event: Event):
        """
        Observer callback: Agent Runtime automatically calls this for every event

        This implements the Observer Pattern where Gateway passively receives
        events instead of channels actively pushing to Gateway.

        Args:
            event: Unified Event from Agent Runtime
        """
        # Broadcast to all WebSocket clients using standardized format
        await self.broadcast_event("agent", event.to_dict())

    async def handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Handle new WebSocket connection"""
        connection = GatewayConnection(websocket, self.config)
        self.connections.add(connection)

        try:
            logger.info(f"New connection from {websocket.remote_address}")
            async for message in websocket:
                if isinstance(message, str):
                    await connection.handle_message(message)
                else:
                    logger.warning(f"Received non-text message: {type(message)}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
        finally:
            self.connections.discard(connection)

    async def broadcast_event(self, event: str, payload: Any = None) -> None:
        """Broadcast event to all connected clients"""
        disconnected = set()
        for connection in self.connections:
            try:
                await connection.send_event(event, payload)
            except Exception as e:
                logger.error(f"Failed to send event to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        self.connections -= disconnected

    async def start(self, start_channels: bool = True) -> None:
        """
        Start the Gateway server

        Args:
            start_channels: If True, start all enabled channels
        """
        host = "127.0.0.1" if self.config.gateway.bind == "loopback" else "0.0.0.0"
        port = self.config.gateway.port

        logger.info(f"Starting Gateway server on {host}:{port}")
        self.running = True

        # Start all enabled channels
        if start_channels:
            channel_results = await self.channel_manager.start_all()
            started = sum(1 for v in channel_results.values() if v)
            logger.info(f"Started {started}/{len(channel_results)} channels")

        async with websockets.serve(self.handle_connection, host, port):
            logger.info(f"Gateway server running on ws://{host}:{port}")
            logger.info(
                f"ChannelManager: {len(self.channel_manager.list_running())} channels running"
            )
            # Keep server running
            while self.running:
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the Gateway server"""
        logger.info("Stopping Gateway server")
        self.running = False

        # Stop all channels first
        await self.channel_manager.stop_all()
        logger.info("All channels stopped")

        # Close all WebSocket connections
        for connection in list(self.connections):
            try:
                await connection.websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

        self.connections.clear()
        logger.info("Gateway server stopped")
