"""File system watcher for automatic memory sync

Watches directories and triggers re-indexing on changes.
Uses watchdog library.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


class FileWatcher:
    """
    File system watcher
    
    Watches directories for changes and triggers callbacks.
    """
    
    def __init__(self):
        """Initialize file watcher"""
        self.observer = None
        self.handlers: dict[str, Callable] = {}
        self.running = False
    
    async def start(
        self,
        watch_paths: list[Path],
        on_change: Callable[[Path], Awaitable[None]],
    ) -> None:
        """
        Start watching paths
        
        Args:
            watch_paths: Paths to watch
            on_change: Callback for changes
        """
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            raise RuntimeError(
                "watchdog not installed. Install with: pip install watchdog"
            )
        
        logger.info(f"Starting file watcher for {len(watch_paths)} paths")
        
        # Create event handler
        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, callback: Callable):
                self.callback = callback
                self._pending_changes: set[Path] = set()
                self._debounce_task: asyncio.Task | None = None
            
            def on_any_event(self, event):
                """Handle any file system event"""
                if event.is_directory:
                    return
                
                # Get path
                path = Path(event.src_path)
                
                # Add to pending
                self._pending_changes.add(path)
                
                # Debounce - schedule callback
                if self._debounce_task:
                    self._debounce_task.cancel()
                
                self._debounce_task = asyncio.create_task(
                    self._debounced_callback()
                )
            
            async def _debounced_callback(self):
                """Debounced callback - wait for changes to settle"""
                await asyncio.sleep(0.5)  # 500ms debounce
                
                # Process pending changes
                for path in self._pending_changes:
                    try:
                        await self.callback(path)
                    except Exception as e:
                        logger.error(f"Error in change callback: {e}", exc_info=True)
                
                # Clear pending
                self._pending_changes.clear()
        
        # Create observer
        self.observer = Observer()
        
        # Add handlers for each path
        for path in watch_paths:
            if not path.exists():
                logger.warning(f"Watch path does not exist: {path}")
                continue
            
            handler = ChangeHandler(on_change)
            self.observer.schedule(handler, str(path), recursive=True)
            
            logger.debug(f"Watching: {path}")
        
        # Start observer
        self.observer.start()
        self.running = True
        
        logger.info("File watcher started")
    
    async def stop(self) -> None:
        """Stop watching"""
        if not self.running:
            return
        
        logger.info("Stopping file watcher")
        
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.running = False
        
        logger.info("File watcher stopped")
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()
