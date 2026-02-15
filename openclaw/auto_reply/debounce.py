"""
Message debouncing to batch rapid messages.

Batches rapid messages from the same sender to avoid
generating multiple separate responses.

Matches openclaw/src/web/auto-reply/debounce.ts
"""
from __future__ import annotations

import asyncio
from typing import Callable


class MessageDebouncer:
    """
    Batches rapid messages from same sender.
    
    When multiple messages arrive quickly from the same peer,
    they are batched together and processed as a single conversation.
    
    Usage:
        debouncer = MessageDebouncer(interval_ms=2000)
        
        async def process_messages(peer_id: str, messages: list[dict]):
            # Handle batched messages
            pass
        
        # Add messages as they arrive
        await debouncer.add_message(
            peer_id="user_123",
            message={"text": "Hello"},
            callback=process_messages
        )
    """
    
    def __init__(self, interval_ms: int = 2000):
        """
        Initialize message debouncer.
        
        Args:
            interval_ms: Debounce interval in milliseconds (default 2000ms)
        """
        self._pending: dict[str, list[dict]] = {}  # peer_id -> [messages]
        self._timers: dict[str, asyncio.Task] = {}  # peer_id -> timer task
        self._callbacks: dict[str, Callable] = {}  # peer_id -> callback
        self._interval = interval_ms / 1000.0  # Convert to seconds
    
    async def add_message(
        self,
        peer_id: str,
        message: dict,
        callback: Callable
    ):
        """
        Add message to batch, resets timer.
        
        Args:
            peer_id: Peer identifier
            message: Message dict
            callback: Callback to invoke with batched messages
                     Signature: async def callback(peer_id: str, messages: list[dict])
        """
        if not peer_id:
            return
        
        # Initialize pending list if needed
        if peer_id not in self._pending:
            self._pending[peer_id] = []
        
        # Add message to batch
        self._pending[peer_id].append(message)
        
        # Store callback
        self._callbacks[peer_id] = callback
        
        # Cancel existing timer if any
        if peer_id in self._timers:
            self._timers[peer_id].cancel()
        
        # Create new timer
        self._timers[peer_id] = asyncio.create_task(
            self._debounce_timer(peer_id)
        )
    
    async def _debounce_timer(self, peer_id: str):
        """
        Timer that fires after debounce interval.
        
        Args:
            peer_id: Peer identifier
        """
        try:
            # Wait for debounce interval
            await asyncio.sleep(self._interval)
            
            # Get batched messages
            messages = self._pending.get(peer_id, [])
            callback = self._callbacks.get(peer_id)
            
            # Clear state
            if peer_id in self._pending:
                del self._pending[peer_id]
            if peer_id in self._timers:
                del self._timers[peer_id]
            if peer_id in self._callbacks:
                del self._callbacks[peer_id]
            
            # Invoke callback with batched messages
            if messages and callback:
                await callback(peer_id, messages)
        
        except asyncio.CancelledError:
            # Timer was cancelled (new message arrived)
            pass
    
    async def flush(self, peer_id: str):
        """
        Immediately process pending messages for a peer.
        
        Args:
            peer_id: Peer identifier
        """
        if peer_id not in self._pending:
            return
        
        # Cancel timer
        if peer_id in self._timers:
            self._timers[peer_id].cancel()
            del self._timers[peer_id]
        
        # Get batched messages
        messages = self._pending.get(peer_id, [])
        callback = self._callbacks.get(peer_id)
        
        # Clear state
        if peer_id in self._pending:
            del self._pending[peer_id]
        if peer_id in self._callbacks:
            del self._callbacks[peer_id]
        
        # Invoke callback
        if messages and callback:
            await callback(peer_id, messages)
    
    async def flush_all(self):
        """Flush all pending messages immediately"""
        peer_ids = list(self._pending.keys())
        for peer_id in peer_ids:
            await self.flush(peer_id)
    
    def is_pending(self, peer_id: str) -> bool:
        """Check if peer has pending messages"""
        return peer_id in self._pending
    
    def count_pending(self, peer_id: str) -> int:
        """Get number of pending messages for peer"""
        return len(self._pending.get(peer_id, []))
    
    def clear(self):
        """Clear all pending messages and timers"""
        # Cancel all timers
        for task in self._timers.values():
            task.cancel()
        
        self._pending.clear()
        self._timers.clear()
        self._callbacks.clear()


__all__ = [
    "MessageDebouncer",
]
