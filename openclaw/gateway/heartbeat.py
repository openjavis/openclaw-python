"""
Periodic heartbeat system for agents.

Executes periodic agent turns in the main session to:
- Keep sessions alive
- Monitor system health
- Provide status updates

Reference: openclaw/docs/concepts/heartbeat.md
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class HeartbeatConfig:
    """Heartbeat configuration"""
    
    enabled: bool = True
    interval_minutes: int = 30  # Default 30m (60m for Anthropic OAuth)
    active_hours: tuple[int, int] | None = None  # (start_hour, end_hour) in 24h format
    show_ok: bool = True  # Show OK acknowledgments in channels
    show_alerts: bool = True  # Show alert messages in channels
    use_indicator: bool = False  # Use indicator instead of full messages


class HeartbeatManager:
    """
    Manage periodic heartbeat agent turns.
    
    The heartbeat system executes periodic agent turns in the main session
    to provide health monitoring and keep connections alive.
    
    Features:
    - Configurable interval (default 30m)
    - Active hours restriction (e.g., 9am-6pm)
    - HEARTBEAT_OK special handling
    - Per-channel visibility settings
    
    Usage:
        config = HeartbeatConfig(
            enabled=True,
            interval_minutes=30,
            active_hours=(9, 18)  # 9am-6pm
        )
        
        manager = HeartbeatManager(config, agent_runtime)
        await manager.start()
        
        # Later...
        await manager.stop()
    """
    
    def __init__(
        self, 
        config: HeartbeatConfig, 
        agent_runtime,
        session_key: str = "agent:main:main"
    ):
        """
        Initialize heartbeat manager.
        
        Args:
            config: Heartbeat configuration
            agent_runtime: Agent runtime for executing turns
            session_key: Session key for heartbeat turns
        """
        self._config = config
        self._agent_runtime = agent_runtime
        self._session_key = session_key
        self._task: asyncio.Task | None = None
        self._running = False
    
    async def start(self) -> None:
        """Start heartbeat loop"""
        if not self._config.enabled:
            logger.info("Heartbeat disabled by config")
            return
        
        if self._running:
            logger.warning("Heartbeat already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            f"Heartbeat started: interval={self._config.interval_minutes}m, "
            f"active_hours={self._config.active_hours}"
        )
    
    async def stop(self) -> None:
        """Stop heartbeat loop"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("Heartbeat stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat execution loop"""
        while self._running:
            try:
                # Wait for interval
                await asyncio.sleep(self._config.interval_minutes * 60)
                
                # Check if in active hours
                if not self._is_active_hour():
                    logger.debug("Skipping heartbeat: outside active hours")
                    continue
                
                # Execute heartbeat turn
                await self._execute_heartbeat()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat execution error: {e}", exc_info=True)
    
    def _is_active_hour(self) -> bool:
        """
        Check if current hour is within active hours.
        
        Returns:
            True if within active hours or no restriction, False otherwise
        """
        if not self._config.active_hours:
            return True  # No restriction
        
        current_hour = datetime.now().hour
        start, end = self._config.active_hours
        
        if start <= end:
            # Normal range (e.g., 9-18)
            return start <= current_hour < end
        else:
            # Wrap around midnight (e.g., 22-6)
            return current_hour >= start or current_hour < end
    
    async def _execute_heartbeat(self) -> None:
        """
        Execute heartbeat agent turn.
        
        Runs agent in main session with special HEARTBEAT_OK handling.
        """
        try:
            logger.info("Executing heartbeat turn")
            
            # Execute agent turn with heartbeat message
            async for event in self._agent_runtime.run_turn(
                session_key=self._session_key,
                messages=[{
                    "role": "user",
                    "content": "HEARTBEAT_OK"
                }],
                stream=True
            ):
                # Log events but don't block
                if event.type == "agent_error":
                    logger.error(f"Heartbeat error: {event.data}")
                elif event.type == "agent_complete":
                    logger.info("Heartbeat completed successfully")
            
        except Exception as e:
            logger.error(f"Heartbeat execution failed: {e}", exc_info=True)
    
    def is_running(self) -> bool:
        """Check if heartbeat is running"""
        return self._running
    
    def get_config(self) -> HeartbeatConfig:
        """Get current configuration"""
        return self._config
    
    def update_config(self, config: HeartbeatConfig) -> None:
        """
        Update configuration (requires restart).
        
        Args:
            config: New heartbeat configuration
        """
        self._config = config


__all__ = [
    "HeartbeatConfig",
    "HeartbeatManager",
]
