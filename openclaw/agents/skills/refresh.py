"""Skills refresh and watching (matches TypeScript agents/skills/refresh.ts)

Watches skills directories for changes and reloads automatically.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Global state
_skills_snapshot_version = 0
_watchers: dict[str, asyncio.Task] = {}
_change_listeners: list[Callable[[], Any]] = []


def bump_skills_snapshot_version() -> int:
    """Bump the skills snapshot version counter"""
    global _skills_snapshot_version
    _skills_snapshot_version += 1
    logger.debug(f"Skills snapshot version bumped to {_skills_snapshot_version}")
    return _skills_snapshot_version


def get_skills_snapshot_version() -> int:
    """Get current skills snapshot version"""
    return _skills_snapshot_version


def register_skills_change_listener(listener: Callable[[], Any]) -> Callable:
    """Register a listener for skills changes. Returns unsubscribe function."""
    _change_listeners.append(listener)
    
    def unsubscribe():
        if listener in _change_listeners:
            _change_listeners.remove(listener)
    
    return unsubscribe


async def _notify_change_listeners() -> None:
    """Notify all change listeners"""
    for listener in _change_listeners:
        try:
            result = listener()
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.error(f"Skills change listener error: {e}")


async def _watch_directory(
    directory: Path,
    poll_interval: float = 5.0,
) -> None:
    """Watch a directory for file changes"""
    # Track file modification times
    last_mtimes: dict[str, float] = {}
    
    def scan() -> dict[str, float]:
        mtimes = {}
        if directory.exists():
            for item in directory.rglob("*"):
                if item.is_file():
                    try:
                        mtimes[str(item)] = os.path.getmtime(item)
                    except OSError:
                        pass
        return mtimes
    
    # Initial scan
    last_mtimes = scan()
    
    logger.info(f"Watching skills directory: {directory}")
    
    while True:
        try:
            await asyncio.sleep(poll_interval)
            
            current_mtimes = scan()
            
            # Detect changes
            changed = False
            
            # Check for new or modified files
            for path, mtime in current_mtimes.items():
                if path not in last_mtimes or last_mtimes[path] != mtime:
                    changed = True
                    logger.info(f"Skill file changed: {path}")
                    break
            
            # Check for deleted files
            if not changed:
                for path in last_mtimes:
                    if path not in current_mtimes:
                        changed = True
                        logger.info(f"Skill file deleted: {path}")
                        break
            
            if changed:
                last_mtimes = current_mtimes
                bump_skills_snapshot_version()
                await _notify_change_listeners()
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Skills watcher error: {e}")


def ensure_skills_watcher(
    directory: Path,
    poll_interval: float = 5.0,
) -> None:
    """Ensure a watcher is running for a skills directory"""
    dir_key = str(directory)
    
    if dir_key in _watchers and not _watchers[dir_key].done():
        return  # Already watching
    
    task = asyncio.create_task(_watch_directory(directory, poll_interval))
    _watchers[dir_key] = task


def stop_all_watchers() -> None:
    """Stop all skills watchers"""
    for dir_key, task in _watchers.items():
        if not task.done():
            task.cancel()
    _watchers.clear()
    logger.info("All skills watchers stopped")
