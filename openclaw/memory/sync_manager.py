"""Sync manager coordinates auto-sync and file watching"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from .file_watcher import FileWatcher
from .session_exporter import SessionExporter
from .builtin_manager import BuiltinMemoryManager

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Sync manager for automated memory indexing
    
    Coordinates:
    - File system watching
    - Session export tracking
    - Periodic sync
    - Auto re-indexing
    """
    
    def __init__(
        self,
        memory_manager: BuiltinMemoryManager,
        workspace_path: Path,
    ):
        """
        Initialize sync manager
        
        Args:
            memory_manager: Memory manager instance
            workspace_path: Workspace root path
        """
        self.memory_manager = memory_manager
        self.workspace_path = workspace_path
        
        # Components
        self.file_watcher = FileWatcher()
        self.session_exporter = SessionExporter()
        
        # State
        self.running = False
        self._sync_task: asyncio.Task | None = None
    
    async def start(self) -> None:
        """Start sync manager"""
        if self.running:
            logger.warning("Sync manager already running")
            return
        
        logger.info("Starting sync manager")
        
        # Determine watch paths
        watch_paths = self._get_watch_paths()
        
        # Start file watcher
        await self.file_watcher.start(
            watch_paths=watch_paths,
            on_change=self._handle_file_change,
        )
        
        # Start periodic sync
        self._sync_task = asyncio.create_task(self._periodic_sync())
        
        self.running = True
        
        logger.info("Sync manager started")
    
    async def stop(self) -> None:
        """Stop sync manager"""
        if not self.running:
            return
        
        logger.info("Stopping sync manager")
        
        # Stop file watcher
        await self.file_watcher.stop()
        
        # Cancel periodic sync
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        self.running = False
        
        logger.info("Sync manager stopped")
    
    def _get_watch_paths(self) -> list[Path]:
        """Get paths to watch"""
        paths = []
        
        # Memory directories
        memory_dir = self.workspace_path / ".openclaw" / "memory"
        if memory_dir.exists():
            paths.append(memory_dir)
        
        # Sessions directory
        sessions_dir = self.workspace_path / ".openclaw" / "sessions"
        if sessions_dir.exists():
            paths.append(sessions_dir)
        
        # Docs directory
        docs_dir = self.workspace_path / "docs"
        if docs_dir.exists():
            paths.append(docs_dir)
        
        return paths
    
    async def _handle_file_change(self, path: Path) -> None:
        """
        Handle file change
        
        Args:
            path: Changed file path
        """
        logger.debug(f"File changed: {path}")
        
        # Determine source type
        from .types import MemorySource
        
        if ".openclaw/sessions" in str(path):
            source = MemorySource.SESSIONS
        elif "docs" in str(path):
            source = MemorySource.MEMORY
        else:
            source = MemorySource.MEMORY
        
        # Re-index file
        try:
            chunks = await self.memory_manager.add_file(path, source)
            logger.info(f"Re-indexed {path}: {chunks} chunks")
        except Exception as e:
            logger.error(f"Error re-indexing {path}: {e}", exc_info=True)
    
    async def _periodic_sync(self) -> None:
        """Periodic sync task"""
        while True:
            try:
                # Wait interval (30 minutes)
                await asyncio.sleep(1800)
                
                # Run sync
                logger.info("Running periodic sync")
                stats = await self.memory_manager.sync()
                
                logger.info(
                    f"Periodic sync complete: "
                    f"{stats.get('files_added', 0)} added, "
                    f"{stats.get('files_updated', 0)} updated, "
                    f"{stats.get('files_removed', 0)} removed"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sync: {e}", exc_info=True)
    
    async def export_session_if_needed(
        self,
        session_id: str,
        message: dict[str, Any],
        session_path: Path,
    ) -> None:
        """
        Track session message and export if threshold reached
        
        Args:
            session_id: Session ID
            message: New message
            session_path: Path to session file
        """
        # Track message
        should_export = self.session_exporter.track_message(session_id, message)
        
        # Export if needed
        if should_export:
            await self.session_exporter.export_session(
                session_id=session_id,
                session_path=session_path,
                memory_manager=self.memory_manager,
            )
    
    def get_stats(self) -> dict[str, Any]:
        """Get sync manager statistics"""
        return {
            "running": self.running,
            "watcher_running": self.file_watcher.running,
            "exporter_stats": self.session_exporter.get_stats(),
        }
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()
