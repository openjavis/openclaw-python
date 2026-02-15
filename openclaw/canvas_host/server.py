"""
Canvas Host Server.

WebSocket server for A2UI canvas rendering with live reload.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Set

import websockets
from websockets.server import WebSocketServerProtocol
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class CanvasFileWatcher(FileSystemEventHandler):
    """Watch canvas files for changes"""
    
    def __init__(self, server: 'CanvasHostServer'):
        self.server = server
    
    def on_modified(self, event):
        """Handle file modification"""
        if not event.is_directory:
            asyncio.create_task(self.server._broadcast_reload())


class CanvasHostServer:
    """
    Canvas host server for A2UI rendering.
    
    Paths:
    - /__openclaw__/a2ui/* - A2UI resources (scaffold)
    - /__openclaw__/canvas/* - User-editable HTML/CSS/JS
    - /__openclaw__/ws - Live reload WebSocket
    
    Features:
    - Static file serving from ~/.openclaw/canvas
    - File monitoring with watchdog
    - Live reload on file changes
    """
    
    def __init__(self, canvas_root: Path | None = None):
        self.canvas_root = canvas_root or (Path.home() / ".openclaw" / "canvas")
        self.canvas_root.mkdir(parents=True, exist_ok=True)
        
        self.host = "127.0.0.1"
        self.port = 0
        self._server: Any = None
        self._clients: Set[WebSocketServerProtocol] = set()
        self._observer: Observer | None = None
        self._running = False
    
    async def start(self, host: str | None = None, port: int | None = None):
        """
        Start canvas host server.
        
        Args:
            host: Host to bind to
            port: Port to bind to (0 for auto-assignment)
        """
        if host:
            self.host = host
        if port is not None:
            self.port = port
        
        self._running = True
        
        # Start WebSocket server for live reload
        self._server = await websockets.serve(
            self._handle_ws_connection,
            self.host,
            self.port
        )
        
        # Get actual port
        if self.port == 0:
            self.port = self._server.sockets[0].getsockname()[1]
        
        # Start file watcher
        self._start_file_watcher()
        
        logger.info(f"Canvas host started on {self.host}:{self.port}")
        logger.info(f"Canvas root: {self.canvas_root}")
    
    async def stop(self):
        """Stop canvas host server"""
        self._running = False
        
        # Stop file watcher
        if self._observer:
            self._observer.stop()
            self._observer.join()
        
        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        # Close all clients
        for client in list(self._clients):
            await client.close()
        
        logger.info("Canvas host stopped")
    
    def _start_file_watcher(self):
        """Start watching canvas files"""
        handler = CanvasFileWatcher(self)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.canvas_root), recursive=True)
        self._observer.start()
        logger.info(f"Watching canvas files in {self.canvas_root}")
    
    async def _handle_ws_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket connection for live reload"""
        self._clients.add(websocket)
        logger.info(f"Canvas client connected ({len(self._clients)} total)")
        
        try:
            async for message in websocket:
                # Echo back or handle commands
                pass
        
        finally:
            self._clients.discard(websocket)
            logger.info(f"Canvas client disconnected ({len(self._clients)} total)")
    
    async def _broadcast_reload(self):
        """Broadcast reload message to all connected clients"""
        if not self._clients:
            return
        
        message = '{"type": "reload"}'
        
        for client in list(self._clients):
            try:
                await client.send(message)
            except Exception as e:
                logger.error(f"Error sending reload: {e}")
                self._clients.discard(client)
        
        logger.debug(f"Broadcasted reload to {len(self._clients)} clients")
    
    def get_canvas_file(self, path: str) -> bytes | None:
        """
        Get canvas file content.
        
        Args:
            path: Relative path within canvas root
            
        Returns:
            File content or None if not found
        """
        file_path = self.canvas_root / path.lstrip('/')
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        try:
            return file_path.read_bytes()
        except Exception as e:
            logger.error(f"Error reading canvas file {file_path}: {e}")
            return None


__all__ = [
    "CanvasHostServer",
]
