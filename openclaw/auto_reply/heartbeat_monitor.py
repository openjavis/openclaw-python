"""
Heartbeat monitoring for auto-reply channels.

Monitors channel health with watchdog timer, triggering
health checks if no messages received within timeout.

Matches openclaw auto-reply heartbeat logic.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    """
    Monitors channel with heartbeat timeout.
    
    If no messages received for timeout period, triggers
    health check callback to ensure channel is still alive.
    
    Usage:
        async def health_check(channel_id: str):
            # Check if channel is still connected
            pass
        
        monitor = HeartbeatMonitor(
            channel_id="telegram",
            timeout_seconds=1800,  # 30 minutes
            health_check_callback=health_check
        )
        
        await monitor.start()
        
        # Reset watchdog on message
        monitor.reset()
        
        # Stop monitoring
        await monitor.stop()
    """
    
    def __init__(
        self,
        channel_id: str,
        timeout_seconds: int = 1800,  # 30 minutes default
        health_check_callback: Callable[[str], None] | None = None
    ):
        """
        Initialize heartbeat monitor.
        
        Args:
            channel_id: Channel identifier
            timeout_seconds: Timeout in seconds (default 1800s = 30min)
            health_check_callback: Callback to invoke on timeout
                                  Signature: async def callback(channel_id: str)
        """
        self._channel_id = channel_id
        self._timeout = timeout_seconds
        self._health_check_callback = health_check_callback
        self._timer_task: asyncio.Task | None = None
        self._running = False
    
    async def start(self):
        """Start heartbeat monitoring"""
        if self._running:
            return
        
        self._running = True
        self._timer_task = asyncio.create_task(self._watchdog())
        
        logger.info(
            f"Heartbeat monitor started for {self._channel_id} "
            f"(timeout: {self._timeout}s)"
        )
    
    async def stop(self):
        """Stop heartbeat monitoring"""
        self._running = False
        
        if self._timer_task:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
            self._timer_task = None
        
        logger.info(f"Heartbeat monitor stopped for {self._channel_id}")
    
    def reset(self):
        """
        Reset watchdog timer (call this on message receipt).
        
        Cancels current timer and starts a new one.
        """
        if not self._running:
            return
        
        # Cancel existing timer
        if self._timer_task:
            self._timer_task.cancel()
        
        # Start new timer
        self._timer_task = asyncio.create_task(self._watchdog())
    
    async def _watchdog(self):
        """Watchdog timer that fires after timeout"""
        try:
            await asyncio.sleep(self._timeout)
            
            # Timeout reached - trigger health check
            logger.warning(
                f"Heartbeat timeout for {self._channel_id} "
                f"(no messages for {self._timeout}s)"
            )
            
            if self._health_check_callback:
                try:
                    if asyncio.iscoroutinefunction(self._health_check_callback):
                        await self._health_check_callback(self._channel_id)
                    else:
                        self._health_check_callback(self._channel_id)
                except Exception as e:
                    logger.error(
                        f"Health check callback failed for {self._channel_id}: {e}",
                        exc_info=True
                    )
            
            # Restart timer
            if self._running:
                self._timer_task = asyncio.create_task(self._watchdog())
        
        except asyncio.CancelledError:
            # Timer cancelled (reset called)
            pass
    
    def is_running(self) -> bool:
        """Check if monitor is running"""
        return self._running


async def monitor_with_heartbeat(
    channel_id: str,
    message_handler: Callable,
    timeout: int = 1800,
    health_check: Callable | None = None
):
    """
    Monitor channel with heartbeat timeout.
    
    Wraps message handler with heartbeat monitoring.
    
    Args:
        channel_id: Channel identifier
        message_handler: Async message handler function
        timeout: Heartbeat timeout in seconds
        health_check: Optional health check callback
        
    Usage:
        async def handle_message(message):
            # Process message
            pass
        
        async def check_health(channel_id):
            # Check if channel alive
            pass
        
        await monitor_with_heartbeat(
            channel_id="telegram",
            message_handler=handle_message,
            timeout=1800,
            health_check=check_health
        )
    """
    monitor = HeartbeatMonitor(
        channel_id=channel_id,
        timeout_seconds=timeout,
        health_check_callback=health_check
    )
    
    await monitor.start()
    
    # Wrap handler to reset heartbeat
    async def wrapped_handler(*args, **kwargs):
        try:
            # Reset heartbeat on message
            monitor.reset()
            
            # Call original handler
            return await message_handler(*args, **kwargs)
        except Exception as e:
            logger.error(f"Message handler error: {e}", exc_info=True)
            raise
    
    return wrapped_handler, monitor


__all__ = [
    "HeartbeatMonitor",
    "monitor_with_heartbeat",
]
