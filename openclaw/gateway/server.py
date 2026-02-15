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
from __future__ import annotations


import asyncio
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Any, Optional

# Use aiohttp for unified HTTP + WebSocket server (matches openclaw-ts)
from aiohttp import web, WSMsgType
import aiohttp

from openclaw.gateway.auth import (
    AuthMode,
    AuthMethod,
    authorize_gateway_connect,
    is_loopback_address,
    validate_auth_config,
)
from openclaw.gateway.authorization import AuthContext, authorize_gateway_method
from openclaw.gateway.device_auth import (
    DeviceIdentity,
    authorize_device_identity,
)
from openclaw.gateway.error_codes import (
    ErrorCode,
    InvalidRequestError,
    NotLinkedError,
    UnavailableError,
    error_shape,
)
from openclaw.gateway.protocol.validators import validate_method_params

from ..config import ClawdbotConfig
from ..events import Event
from .channel_manager import ChannelManager, discover_channel_plugins
from .handlers import get_method_handler
from .protocol import ErrorShape, EventFrame, RequestFrame, ResponseFrame
from .protocol.frames import ConnectRequest, HelloResponse

logger = logging.getLogger(__name__)


class GatewayConnection:
    """Represents a single WebSocket connection (aiohttp WebSocketResponse)"""

    def __init__(self, websocket: web.WebSocketResponse, config: ClawdbotConfig, gateway: "GatewayServer" = None, remote_addr: str = ""):
        self.websocket = websocket
        self.config = config
        self.gateway = gateway  # Reference to parent gateway server
        self.remote_addr = remote_addr  # Store remote address for logging
        self.authenticated = False
        self.client_info: dict[str, Any] | None = None
        self.protocol_version = 1
        self.auth_context = AuthContext(role="operator", scopes=set())
        self.nonce: Optional[str] = None
        self.connect_challenge_sent = False

    async def send_response(
        self, request_id: str | int, payload: Any = None, error: ErrorShape | None = None
    ) -> None:
        """Send response frame (supports JSON-RPC 2.0 format)"""
        # Send JSON-RPC 2.0 format
        if error:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603 if error.code == "INTERNAL_ERROR" else -32601,
                    "message": error.message,
                },
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": payload,
            }
        # aiohttp: send_str instead of send
        await self.websocket.send_str(json.dumps(response))

    async def send_event(self, event: str, payload: Any = None) -> None:
        """Send event frame"""
        event_frame = EventFrame(event=event, payload=payload)
        # aiohttp: send_str instead of send
        await self.websocket.send_str(event_frame.model_dump_json())

    async def handle_message(self, message: str) -> None:
        """Handle incoming message"""
        try:
            data = json.loads(message)
            
            # Support both custom frame format and standard JSON-RPC 2.0
            if "jsonrpc" in data:
                # Standard JSON-RPC 2.0 format
                request = RequestFrame(
                    type="req",
                    id=data.get("id"),
                    method=data.get("method"),
                    params=data.get("params", {}),
                )
                await self.handle_request(request)
            elif data.get("type") == "req":
                # Custom frame format
                request = RequestFrame(**data)
                await self.handle_request(request)
            else:
                logger.warning(f"Unknown message format: {data}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def handle_request(self, request: RequestFrame) -> None:
        """Handle request frame with authorization"""
        try:
            # Special handling for connect method
            if request.method == "connect":
                await self.handle_connect(request)
                return

            # Check authentication for other methods
            if not self.authenticated and request.method not in ("health", "ping"):
                await self.send_response(
                    request.id,
                    error=ErrorShape(
                        code="AUTH_REQUIRED",
                        message="Authentication required. Send 'connect' request first.",
                    ),
                )
                return

            # Check authorization (role/scope based)
            if not authorize_gateway_method(request.method, self.auth_context):
                await self.send_response(
                    request.id,
                    error=ErrorShape(
                        code="PERMISSION_DENIED",
                        message=f"Insufficient permissions for method '{request.method}'",
                    ),
                )
                logger.warning(
                    f"Permission denied: method={request.method}, "
                    f"role={self.auth_context.role}, "
                    f"scopes={self.auth_context.scopes}"
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

            # Validate parameters
            try:
                validated_params = validate_method_params(request.method, request.params or {})
                # Convert Pydantic model to dict if necessary
                if hasattr(validated_params, "model_dump"):
                    params_dict = validated_params.model_dump()
                else:
                    params_dict = request.params or {}
            except Exception as e:
                await self.send_response(
                    request.id,
                    error=ErrorShape(
                        code="INVALID_REQUEST",
                        message=f"Invalid parameters: {str(e)}"
                    ),
                )
                logger.warning(f"Parameter validation failed for {request.method}: {e}")
                return

            # Execute handler
            result = await handler(self, params_dict)
            await self.send_response(request.id, payload=result)

        except Exception as e:
            logger.error(f"Error handling request {request.method}: {e}", exc_info=True)
            await self.send_response(
                request.id, error=ErrorShape(code="INTERNAL_ERROR", message=str(e))
            )

    async def handle_connect(self, request: RequestFrame) -> None:
        """Handle connection handshake with authentication"""
        try:
            connect_req = ConnectRequest(**(request.params or {}))

            # Negotiate protocol version (max is 3)
            negotiated_protocol = min(connect_req.maxProtocol, 3)

            # Extract auth params
            auth_params = connect_req.auth or {}
            request_token = auth_params.get("token")
            request_password = auth_params.get("password")
            
            # Extract device identity if provided
            device_identity = None
            if connect_req.deviceIdentity:
                device_identity = DeviceIdentity(
                    id=connect_req.deviceIdentity.get("id", ""),
                    public_key=connect_req.deviceIdentity.get("publicKey", ""),
                    signature=connect_req.deviceIdentity.get("signature", ""),
                    signed_at=connect_req.deviceIdentity.get("signedAt", ""),
                    nonce=connect_req.deviceIdentity.get("nonce")
                )
            
            # Get client IP (remote_addr is already stored in __init__)
            # self.remote_addr is a string like "127.0.0.1:12345"
            client_ip = self.remote_addr.split(':')[0] if self.remote_addr else None
            
            # Check if local direct (bypass auth for loopback)
            if client_ip and is_loopback_address(client_ip):
                logger.info("Local direct connection, bypassing auth")
                auth_result_ok = True
                auth_method = AuthMethod.LOCAL_DIRECT
            else:
                # Perform authentication
                # TODO: Get auth config from self.config
                config_token = getattr(self.config, "gateway_token", None)
                config_password = getattr(self.config, "gateway_password", None)
                auth_mode = AuthMode.TOKEN if config_token else AuthMode.PASSWORD
                
                auth_result = authorize_gateway_connect(
                    auth_mode=auth_mode,
                    config_token=config_token,
                    config_password=config_password,
                    request_token=request_token,
                    request_password=request_password,
                    allow_tailscale=False,  # TODO: Get from config
                    client_ip=client_ip,
                )
                
                auth_result_ok = auth_result.ok
                auth_method = auth_result.method
                
                # If basic auth failed but device identity provided, try device auth
                if not auth_result_ok and device_identity:
                    device_result = authorize_device_identity(
                        device_identity,
                        nonce=self.nonce,
                        require_nonce=True
                    )
                    if device_result.ok:
                        auth_result_ok = True
                        auth_method = AuthMethod.DEVICE_TOKEN
                
                if not auth_result_ok:
                    await self.send_response(
                        request.id,
                        error=ErrorShape(
                            code="AUTH_FAILED",
                            message=auth_result.reason or "Authentication failed"
                        )
                    )
                    logger.warning(f"Authentication failed: {auth_result.reason}")
                    return

            # Authentication successful
            self.client_info = connect_req.client
            self.protocol_version = negotiated_protocol
            self.authenticated = True
            
            # Set auth context with role and scopes
            role = connect_req.role or "operator"
            scopes = set(connect_req.scopes or [])
            
            # Default scopes for operator role
            if role == "operator" and not scopes:
                scopes = {
                    "operator.admin",
                    "operator.read",
                    "operator.write",
                    "operator.approvals",
                    "operator.pairing"
                }
            
            self.auth_context = AuthContext(
                role=role,
                scopes=scopes,
                user=getattr(auth_result, "user", None) if auth_result_ok and not auth_method == AuthMethod.LOCAL_DIRECT else None,
                device_id=device_identity.id if device_identity else None
            )

            # Send hello response
            hello = HelloResponse(
                protocol=negotiated_protocol,
                server={
                    "name": "openclaw-python",
                    "version": "0.6.0",
                    "platform": "python"
                },
                features={
                    "agent": True,
                    "chat": True,
                    "sessions": True,
                    "channels": True,
                    "tools": True,
                    "cron": True,
                    "nodes": False,  # Not yet implemented
                    "devices": False,  # Not yet implemented
                },
                snapshot={
                    "sessions": [],
                    "channels": [],
                    "agents": []
                },
            )

            await self.send_response(request.id, payload=hello.model_dump())
            logger.info(
                f"Client connected: {self.client_info}, "
                f"protocol={negotiated_protocol}, "
                f"auth_method={auth_method}, "
                f"role={self.auth_context.role}"
            )

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
        self.http_server = None
        self.http_server_task = None
        self.active_runs: dict[str, asyncio.Task] = {}  # Track active agent runs for abort
        
        # Initialize memory manager (lazy initialization)
        self._memory_manager = None
        
        # Initialize approval manager
        from openclaw.exec.approval_manager import ExecApprovalManager
        self.approval_manager = ExecApprovalManager()

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

        # Initialize wizard RPC handler
        from .wizard_rpc import WizardRPCHandler
        self.wizard_handler = WizardRPCHandler(self)

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

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket upgrade and connection (aiohttp)"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Get remote address
        remote_addr = request.remote or "unknown"
        
        # Create connection
        connection = GatewayConnection(ws, self.config, gateway=self, remote_addr=remote_addr)
        self.connections.add(connection)

        try:
            logger.info(f"New WebSocket connection from {remote_addr}")
            
            # Send connect challenge immediately
            connection.nonce = secrets.token_urlsafe(32)
            connection.connect_challenge_sent = True
            await connection.send_event("connect.challenge", {
                "nonce": connection.nonce,
                "timestamp": int(time.time() * 1000)
            })
            logger.debug(f"Sent connect.challenge with nonce")
            
            # Handle messages (aiohttp pattern)
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await connection.handle_message(msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
        finally:
            self.connections.discard(connection)
            logger.info(f"Connection closed: {remote_addr}")
        
        return ws

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
    
    def get_memory_manager(self):
        """Get or create memory manager (lazy initialization)"""
        if self._memory_manager is None:
            try:
                from openclaw.memory.builtin_manager import BuiltinMemoryManager
                
                # Determine workspace directory
                workspace_dir = Path.home() / ".openclaw" / "workspace"
                if self.agent_runtime and hasattr(self.agent_runtime, 'workspace_dir'):
                    workspace_dir = Path(self.agent_runtime.workspace_dir)
                
                # Use default agent_id
                agent_id = "main"
                if self.config and hasattr(self.config, 'agent') and hasattr(self.config.agent, 'id'):
                    agent_id = self.config.agent.id
                
                self._memory_manager = BuiltinMemoryManager(
                    agent_id=agent_id,
                    workspace_dir=workspace_dir,
                    embedding_provider="openai"
                )
                logger.info(f"Memory manager initialized for agent '{agent_id}' at {workspace_dir}")
            except Exception as e:
                logger.error(f"Failed to initialize memory manager: {e}", exc_info=True)
                return None
        
        return self._memory_manager

    def _get_control_ui_config_script(self) -> str:
        """Generate config injection script (matches openclaw-ts)"""
        return """
    <script>
        window.__OPENCLAW_CONTROL_UI_BASE_PATH__ = "/";
        window.__OPENCLAW_ASSISTANT_NAME__ = "OpenClaw";
        window.__OPENCLAW_ASSISTANT_AVATAR__ = null;
    </script>
    """

    async def serve_control_ui(self, request: web.Request) -> web.Response:
        """Serve Control UI index.html"""
        ui_dir = Path(__file__).parent.parent / "web" / "dist" / "control-ui"
        index_path = ui_dir / "index.html"
        
        if not index_path.exists():
            return web.Response(
                text="Control UI not built. Run: cd openclaw/web/ui-src && npm run build",
                status=503,
                content_type="text/plain"
            )
        
        # Read and inject config
        html = index_path.read_text()
        config_script = self._get_control_ui_config_script()
        html = html.replace("</head>", f"{config_script}</head>")
        
        return web.Response(text=html, content_type="text/html")

    async def serve_control_ui_spa(self, request: web.Request) -> web.Response:
        """SPA fallback: serve static files or index.html"""
        ui_dir = Path(__file__).parent.parent / "web" / "dist" / "control-ui"
        path = request.match_info.get('path', '')
        
        # Check if static file exists
        file_path = ui_dir / path
        if file_path.is_file() and file_path.exists():
            return web.FileResponse(file_path)
        
        # Fallback to index.html for SPA routing
        return await self.serve_control_ui(request)
    
    async def handle_root(self, request: web.Request) -> web.Response | web.WebSocketResponse:
        """Handle root path: WebSocket upgrade or Control UI"""
        # Check if this is a WebSocket upgrade request
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            return await self.handle_websocket(request)
        
        # Otherwise, serve Control UI
        return await self.serve_control_ui(request)

    async def start(self, start_channels: bool = True, enable_tls: bool = False, cert_path: Optional[str] = None, key_path: Optional[str] = None) -> None:
        """
        Start unified Gateway server (HTTP + WebSocket on single port)
        
        This implementation matches openclaw-ts architecture:
        - Single port serves both HTTP (Control UI) and WebSocket (Gateway API)
        - Uses aiohttp for HTTP Upgrade pattern

        Args:
            start_channels: If True, start all enabled channels
            enable_tls: If True, enable TLS/SSL
            cert_path: Path to TLS certificate file
            key_path: Path to TLS key file
        """
        host = "127.0.0.1" if self.config.gateway.bind == "loopback" else "0.0.0.0"
        port = self.config.gateway.port

        # Setup SSL context if TLS is enabled
        ssl_context = None
        if enable_tls:
            if not cert_path or not key_path:
                raise ValueError("TLS enabled but cert_path or key_path not provided")
            
            import ssl
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(cert_path, key_path)
            logger.info("TLS/SSL enabled for Gateway server")

        protocol = "wss" if enable_tls else "ws"
        logger.info(f"Starting unified Gateway server on {host}:{port} (TLS: {enable_tls})")
        self.running = True

        # Create aiohttp application
        app = web.Application()
        
        # Register routes (matches openclaw-ts architecture)
        ui_enabled = getattr(self.config.gateway, 'enable_web_ui', True)
        
        if ui_enabled:
            # Root handles both WebSocket upgrade and Control UI
            app.router.add_get('/', self.handle_root)
            # Dedicated WebSocket endpoint
            app.router.add_get('/ws', self.handle_websocket)
            # SPA fallback for all other paths
            app.router.add_get('/{path:.*}', self.serve_control_ui_spa)
        else:
            # Only WebSocket endpoints
            app.router.add_get('/', self.handle_websocket)
            app.router.add_get('/ws', self.handle_websocket)
        
        logger.info(f"Routes registered: WebSocket on / and /ws, Control UI: {ui_enabled}")

        # Start all enabled channels
        if start_channels:
            channel_results = await self.channel_manager.start_all()
            started = sum(1 for v in channel_results.values() if v)
            logger.info(f"Started {started}/{len(channel_results)} channels")

        # Start aiohttp server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
        await site.start()
        
        logger.info(f"✓ Gateway server running on http{'s' if enable_tls else ''}://{host}:{port}")
        logger.info(f"✓ Control UI available at http{'s' if enable_tls else ''}://{host}:{port}/")
        logger.info(f"✓ WebSocket endpoint: {protocol}://{host}:{port}/ws")
        logger.info(f"✓ ChannelManager: {len(self.channel_manager.list_running())} channels running")

        try:
            # Keep server running
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Gateway server task cancelled, cleaning up...")
            raise
        finally:
            await runner.cleanup()

    # Removed _start_http_server - unified server now handles HTTP + WebSocket on single port
    
    async def stop(self) -> None:
        """Stop the Gateway server gracefully"""
        logger.info("Stopping Gateway server gracefully...")
        self.running = False

        # Stop HTTP server if running
        if self.http_server_task:
            logger.debug("Stopping HTTP server...")
            try:
                self.http_server_task.cancel()
                await asyncio.wait_for(self.http_server_task, timeout=2.0)
            except asyncio.CancelledError:
                logger.debug("HTTP server task cancelled")
            except asyncio.TimeoutError:
                logger.warning("HTTP server stop timed out")
            except Exception as e:
                logger.error(f"Error stopping HTTP server: {e}")

        # Close all WebSocket connections first
        if self.connections:
            logger.debug(f"Closing {len(self.connections)} WebSocket connections...")
            close_tasks = []
            for connection in list(self.connections):
                try:
                    close_tasks.append(connection.websocket.close())
                except Exception as e:
                    logger.debug(f"Error preparing connection close: {e}")
            
            if close_tasks:
                try:
                    await asyncio.wait_for(asyncio.gather(*close_tasks, return_exceptions=True), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("WebSocket close timed out")
            
            self.connections.clear()

        # Stop all channels
        logger.debug("Stopping all channels...")
        try:
            await asyncio.wait_for(self.channel_manager.stop_all(), timeout=3.0)
            logger.debug("All channels stopped")
        except asyncio.TimeoutError:
            logger.warning("Channel stop timed out")
        except Exception as e:
            logger.error(f"Error stopping channels: {e}")

        logger.info("Gateway server stopped gracefully")
