"""Sandbox container registry

Manages hot container reuse and lifecycle.
Matches TypeScript openclaw/src/agents/sandbox/registry.ts
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from .config_hash import compute_sandbox_config_hash
from .constants import HOT_CONTAINER_WINDOW_MS
from .docker import DockerSandbox, DockerSandboxConfig, docker_container_state

logger = logging.getLogger(__name__)


@dataclass
class ContainerEntry:
    """Registry entry for a sandbox container"""
    
    container_name: str
    config_hash: str
    created_at_ms: int
    sandbox: DockerSandbox
    last_used_ms: int


class SandboxRegistry:
    """
    Sandbox container registry
    
    Manages hot container reuse for performance.
    Containers with matching configuration can be reused
    within HOT_CONTAINER_WINDOW_MS (5 minutes).
    """
    
    def __init__(self):
        self._containers: dict[str, ContainerEntry] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
    
    async def get_or_create(
        self,
        config: DockerSandboxConfig,
        workspace_dir: Any = None,
    ) -> DockerSandbox:
        """
        Get existing hot container or create new one
        
        Args:
            config: Sandbox configuration
            workspace_dir: Workspace directory
            
        Returns:
            DockerSandbox instance
        """
        config_hash = compute_sandbox_config_hash(config.to_dict())
        now_ms = int(time.time() * 1000)
        
        async with self._lock:
            # Check for hot container
            for entry in self._containers.values():
                if entry.config_hash != config_hash:
                    continue
                
                # Check if within hot window
                age_ms = now_ms - entry.created_at_ms
                if age_ms > HOT_CONTAINER_WINDOW_MS:
                    continue
                
                # Verify container still exists and is running
                state = await docker_container_state(entry.container_name)
                if not state["exists"] or not state["running"]:
                    # Clean up stale entry
                    del self._containers[entry.container_name]
                    continue
                
                # Reuse hot container
                logger.info(f"Reusing hot sandbox container: {entry.container_name}")
                entry.last_used_ms = now_ms
                return entry.sandbox
            
            # No hot container found, create new one
            sandbox = DockerSandbox(config, workspace_dir)
            container_name = await sandbox.start()
            
            # Register
            entry = ContainerEntry(
                container_name=container_name,
                config_hash=config_hash,
                created_at_ms=now_ms,
                sandbox=sandbox,
                last_used_ms=now_ms,
            )
            
            self._containers[container_name] = entry
            
            # Start cleanup task if not running
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            return sandbox
    
    async def cleanup_old_containers(self):
        """Clean up containers outside hot window"""
        now_ms = int(time.time() * 1000)
        to_remove: list[str] = []
        
        async with self._lock:
            for container_name, entry in self._containers.items():
                age_ms = now_ms - entry.last_used_ms
                
                if age_ms > HOT_CONTAINER_WINDOW_MS:
                    to_remove.append(container_name)
        
        # Remove old containers (outside lock)
        for container_name in to_remove:
            entry = self._containers.get(container_name)
            if entry:
                logger.info(f"Cleaning up old sandbox container: {container_name}")
                try:
                    await entry.sandbox.stop()
                except Exception as e:
                    logger.warning(f"Error stopping container {container_name}: {e}")
                
                async with self._lock:
                    self._containers.pop(container_name, None)
    
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while True:
            try:
                # Run cleanup every minute
                await asyncio.sleep(60)
                await self.cleanup_old_containers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sandbox cleanup error: {e}")
    
    async def cleanup_all(self):
        """Clean up all containers"""
        async with self._lock:
            containers = list(self._containers.values())
        
        for entry in containers:
            try:
                await entry.sandbox.stop()
            except Exception as e:
                logger.warning(f"Error stopping container: {e}")
        
        async with self._lock:
            self._containers.clear()
        
        if self._cleanup_task:
            self._cleanup_task.cancel()


# Global registry instance
_registry: SandboxRegistry | None = None


def get_sandbox_registry() -> SandboxRegistry:
    """Get global sandbox registry instance"""
    global _registry
    if _registry is None:
        _registry = SandboxRegistry()
    return _registry
