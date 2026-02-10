"""Config reloader (matches TypeScript gateway config reloading)

Watches config file for changes and reloads automatically.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ConfigReloader:
    """
    Watches configuration file and reloads on change.
    
    Features:
    - File modification time polling
    - Debounced reload (avoids rapid reloads)
    - Callback notification on reload
    - Error handling with fallback to last known good config
    """
    
    def __init__(
        self,
        config_path: Path,
        reload_fn: Callable[[], Any],
        poll_interval_sec: float = 5.0,
        debounce_sec: float = 1.0,
    ):
        self.config_path = config_path
        self.reload_fn = reload_fn
        self.poll_interval_sec = poll_interval_sec
        self.debounce_sec = debounce_sec
        self._task: asyncio.Task | None = None
        self._last_mtime: float = 0
        self._callbacks: list[Callable[[Any], Any]] = []
    
    def on_reload(self, callback: Callable[[Any], Any]) -> None:
        """Register reload callback"""
        self._callbacks.append(callback)
    
    async def _poll_loop(self) -> None:
        """Poll config file for changes"""
        # Get initial mtime
        if self.config_path.exists():
            self._last_mtime = os.path.getmtime(self.config_path)
        
        logger.info(f"Config reloader watching: {self.config_path}")
        
        while True:
            try:
                await asyncio.sleep(self.poll_interval_sec)
                
                if not self.config_path.exists():
                    continue
                
                current_mtime = os.path.getmtime(self.config_path)
                
                if current_mtime > self._last_mtime:
                    self._last_mtime = current_mtime
                    
                    # Debounce
                    await asyncio.sleep(self.debounce_sec)
                    
                    logger.info("Config file changed, reloading...")
                    
                    try:
                        new_config = self.reload_fn()
                        
                        # Notify callbacks
                        for callback in self._callbacks:
                            try:
                                result = callback(new_config)
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception as e:
                                logger.error(f"Config reload callback error: {e}")
                        
                        logger.info("Config reloaded successfully")
                    except Exception as e:
                        logger.error(f"Config reload failed: {e}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Config reloader error: {e}")
    
    def start(self) -> None:
        """Start config reloader"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_loop())
            logger.info("Config reloader started")
    
    def stop(self) -> None:
        """Stop config reloader"""
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Config reloader stopped")


def apply_config_patch(
    config_data: dict[str, Any],
    patch: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Apply JSON patch operations to config (matches TypeScript merge-patch.ts).
    
    Supports operations:
    - {"op": "add", "path": "/a/b", "value": "x"}
    - {"op": "remove", "path": "/a/b"}
    - {"op": "replace", "path": "/a/b", "value": "y"}
    
    Args:
        config_data: Current config dict
        patch: List of patch operations
    
    Returns:
        Patched config dict
    """
    import copy
    result = copy.deepcopy(config_data)
    
    for op in patch:
        operation = op.get("op")
        path = op.get("path", "")
        value = op.get("value")
        
        # Parse JSON pointer path
        parts = [p for p in path.split("/") if p]
        
        if not parts:
            continue
        
        if operation == "add" or operation == "replace":
            # Navigate to parent
            current = result
            for part in parts[:-1]:
                if isinstance(current, dict):
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                elif isinstance(current, list):
                    idx = int(part)
                    current = current[idx]
            
            # Set value
            last_key = parts[-1]
            if isinstance(current, dict):
                current[last_key] = value
            elif isinstance(current, list):
                idx = int(last_key)
                if operation == "add":
                    current.insert(idx, value)
                else:
                    current[idx] = value
        
        elif operation == "remove":
            # Navigate to parent
            current = result
            for part in parts[:-1]:
                if isinstance(current, dict):
                    current = current.get(part, {})
                elif isinstance(current, list):
                    current = current[int(part)]
            
            # Remove
            last_key = parts[-1]
            if isinstance(current, dict) and last_key in current:
                del current[last_key]
            elif isinstance(current, list):
                del current[int(last_key)]
    
    return result
