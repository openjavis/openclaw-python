"""Gateway WebSocket server implementation"""

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

from ..config import ClawdbotConfig
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
    """Gateway WebSocket server"""

    def __init__(self, config: ClawdbotConfig, agent_runtime=None):
        self.config = config
        self.connections: set[GatewayConnection] = set()
        self.running = False
        self.agent_runtime = agent_runtime
        
        # Register as observer if agent_runtime provided
        if agent_runtime:
            agent_runtime.add_event_listener(self.on_agent_event)
            logger.info("Gateway registered as Agent Runtime observer")
    
    async def on_agent_event(self, event):
        """
        Observer callback: Agent Runtime automatically calls this for every event
        
        This implements the Observer Pattern where Gateway passively receives
        events instead of channels actively pushing to Gateway.
        """
        # Broadcast to all WebSocket clients
        await self.broadcast_event("agent", {
            "type": event.type,
            "data": event.data
        })

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

    async def start(self) -> None:
        """Start the Gateway server"""
        host = "127.0.0.1" if self.config.gateway.bind == "loopback" else "0.0.0.0"
        port = self.config.gateway.port

        logger.info(f"Starting Gateway server on {host}:{port}")
        self.running = True

        async with websockets.serve(self.handle_connection, host, port):
            logger.info(f"Gateway server running on ws://{host}:{port}")
            # Keep server running
            while self.running:
                await asyncio.sleep(1)

    async def stop(self) -> None:
        """Stop the Gateway server"""
        logger.info("Stopping Gateway server")
        self.running = False

        # Close all connections
        for connection in list(self.connections):
            try:
                await connection.websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

        self.connections.clear()
