"""Chrome extension relay for browser control

Provides WebSocket-based communication with Chrome extensions.
Matches TypeScript openclaw/src/browser/extension-relay.ts
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ExtensionRelay:
    """
    Chrome extension relay
    
    Provides communication channel between Python backend and Chrome extensions.
    Uses WebSocket for bi-directional messaging.
    """
    
    def __init__(self, port: int = 9223):
        """
        Initialize extension relay
        
        Args:
            port: WebSocket server port
        """
        self.port = port
        self.server = None
        self.connections: set = set()
        self.handlers: dict[str, Callable] = {}
        self.running = False
    
    async def start(self) -> None:
        """Start relay server"""
        if self.running:
            logger.warning("Extension relay already running")
            return
        
        try:
            import websockets
        except ImportError:
            raise RuntimeError(
                "websockets not installed. Install with: pip install websockets"
            )
        
        logger.info(f"Starting extension relay on port {self.port}")
        
        self.server = await websockets.serve(
            self._handle_connection,
            "localhost",
            self.port
        )
        
        self.running = True
        
        logger.info(f"Extension relay started on ws://localhost:{self.port}")
    
    async def stop(self) -> None:
        """Stop relay server"""
        if not self.running:
            return
        
        logger.info("Stopping extension relay")
        
        # Close all connections
        for conn in self.connections:
            await conn.close()
        
        self.connections.clear()
        
        # Stop server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.running = False
        
        logger.info("Extension relay stopped")
    
    async def _handle_connection(self, websocket, path):
        """Handle WebSocket connection"""
        logger.info(f"Extension connected: {websocket.remote_address}")
        
        self.connections.add(websocket)
        
        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
        finally:
            self.connections.remove(websocket)
            logger.info(f"Extension disconnected: {websocket.remote_address}")
    
    async def _handle_message(self, websocket, message: str) -> None:
        """Handle incoming message"""
        try:
            data = json.loads(message)
            
            msg_type = data.get("type")
            msg_id = data.get("id")
            payload = data.get("payload", {})
            
            logger.debug(f"Received message: {msg_type}")
            
            # Find handler
            handler = self.handlers.get(msg_type)
            
            if handler:
                # Call handler
                result = await handler(payload)
                
                # Send response
                response = {
                    "type": f"{msg_type}_response",
                    "id": msg_id,
                    "payload": result,
                }
                
                await websocket.send(json.dumps(response))
            else:
                logger.warning(f"No handler for message type: {msg_type}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
    
    def register_handler(self, msg_type: str, handler: Callable) -> None:
        """
        Register message handler
        
        Args:
            msg_type: Message type to handle
            handler: Handler function
        """
        self.handlers[msg_type] = handler
        
        logger.debug(f"Registered handler for: {msg_type}")
    
    async def broadcast(self, msg_type: str, payload: Any) -> None:
        """
        Broadcast message to all connections
        
        Args:
            msg_type: Message type
            payload: Message payload
        """
        if not self.connections:
            logger.warning("No connections to broadcast to")
            return
        
        message = json.dumps({
            "type": msg_type,
            "payload": payload,
        })
        
        # Send to all connections
        await asyncio.gather(
            *[conn.send(message) for conn in self.connections],
            return_exceptions=True
        )
        
        logger.debug(f"Broadcasted {msg_type} to {len(self.connections)} connections")
    
    async def send_to_extension(
        self,
        extension_id: str,
        msg_type: str,
        payload: Any
    ) -> None:
        """
        Send message to specific extension
        
        Args:
            extension_id: Extension ID
            msg_type: Message type
            payload: Message payload
        """
        # TODO: Track extensions by ID
        # For now, broadcast
        await self.broadcast(msg_type, payload)
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()
