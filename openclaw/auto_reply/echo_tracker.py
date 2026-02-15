"""
Echo detection to prevent responding to own messages.

Tracks outbound messages to detect when they echo back,
preventing infinite reply loops.

Matches openclaw/src/web/auto-reply/echo-tracker.ts
"""
from __future__ import annotations

import time


class EchoTracker:
    """
    Tracks outbound messages to detect echoes.
    
    When we send a message, we mark it as outbound. If we receive
    that same message back (echo), we can detect it and avoid replying.
    
    Usage:
        tracker = EchoTracker(window_seconds=30)
        
        # Mark message as outbound when sending
        tracker.mark_outbound(message_id="msg_123")
        
        # Check if received message is an echo
        if tracker.is_echo(message_id="msg_123"):
            # Skip this message, it's our own echo
            return
    """
    
    def __init__(self, window_seconds: int = 30):
        """
        Initialize echo tracker.
        
        Args:
            window_seconds: Time window for echo detection (default 30s)
        """
        self._outbound: dict[str, float] = {}  # message_id -> timestamp
        self._window = window_seconds
    
    def mark_outbound(self, message_id: str):
        """
        Mark message as outbound (sent by us).
        
        Args:
            message_id: Message ID to mark
        """
        if not message_id:
            return
        
        self._outbound[message_id] = time.time()
        
        # Cleanup old entries
        self._cleanup()
    
    def is_echo(self, message_id: str) -> bool:
        """
        Check if message is an echo (our own message).
        
        Args:
            message_id: Message ID to check
            
        Returns:
            True if message is an echo, False otherwise
        """
        if not message_id:
            return False
        
        # Check if message ID is in outbound set
        if message_id in self._outbound:
            # Remove from tracking (already processed)
            del self._outbound[message_id]
            return True
        
        return False
    
    def _cleanup(self):
        """Remove expired entries from tracking"""
        now = time.time()
        expired = [
            msg_id for msg_id, ts in self._outbound.items()
            if now - ts > self._window
        ]
        
        for msg_id in expired:
            del self._outbound[msg_id]
    
    def clear(self):
        """Clear all tracked messages"""
        self._outbound.clear()
    
    def count(self) -> int:
        """Get number of tracked outbound messages"""
        return len(self._outbound)


__all__ = [
    "EchoTracker",
]
