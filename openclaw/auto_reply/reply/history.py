"""Message history management

Manages conversation history with LRU eviction.
Matches TypeScript openclaw/src/auto-reply/reply/history.ts
"""
from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """Single history entry"""
    
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)


class MessageHistory:
    """
    Message history manager
    
    Features:
    - Per-session history tracking
    - LRU eviction (max 1000 sessions)
    - Per-session message limits
    - Group chat history limits
    """
    
    def __init__(
        self,
        max_sessions: int = 1000,
        max_messages_per_session: int = 100,
        group_history_limit: int = 50,
    ):
        """
        Initialize message history
        
        Args:
            max_sessions: Maximum number of sessions to track
            max_messages_per_session: Maximum messages per session
            group_history_limit: Message limit for group chats
        """
        self.max_sessions = max_sessions
        self.max_messages_per_session = max_messages_per_session
        self.group_history_limit = group_history_limit
        
        # Session histories: session_key -> list of HistoryEntry
        self._histories: OrderedDict[str, list[HistoryEntry]] = OrderedDict()
    
    def _make_session_key(
        self,
        channel_id: str,
        sender_id: str,
        thread_id: str | None = None
    ) -> str:
        """Make session key"""
        if thread_id:
            return f"{channel_id}:{thread_id}:{sender_id}"
        return f"{channel_id}:{sender_id}"
    
    def add_message(
        self,
        channel_id: str,
        sender_id: str,
        role: str,
        content: str,
        thread_id: str | None = None,
        is_group: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add message to history
        
        Args:
            channel_id: Channel ID
            sender_id: Sender ID
            role: Message role (user/assistant)
            content: Message content
            thread_id: Optional thread ID
            is_group: Whether this is a group chat
            metadata: Optional metadata
        """
        import time
        
        session_key = self._make_session_key(channel_id, sender_id, thread_id)
        
        # Get or create history
        if session_key not in self._histories:
            self._histories[session_key] = []
        
        # Create entry
        entry = HistoryEntry(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        
        # Add to history
        history = self._histories[session_key]
        history.append(entry)
        
        # Determine limit
        if is_group:
            limit = self.group_history_limit
        else:
            limit = self.max_messages_per_session
        
        # Enforce limit
        if len(history) > limit:
            # Remove oldest
            history.pop(0)
        
        # Move to end (LRU)
        self._histories.move_to_end(session_key)
        
        # Enforce max sessions
        while len(self._histories) > self.max_sessions:
            # Remove oldest session
            self._histories.popitem(last=False)
    
    def get_history(
        self,
        channel_id: str,
        sender_id: str,
        thread_id: str | None = None,
        limit: int | None = None,
    ) -> list[HistoryEntry]:
        """
        Get message history for session
        
        Args:
            channel_id: Channel ID
            sender_id: Sender ID
            thread_id: Optional thread ID
            limit: Optional limit (most recent N messages)
            
        Returns:
            List of history entries
        """
        session_key = self._make_session_key(channel_id, sender_id, thread_id)
        
        history = self._histories.get(session_key, [])
        
        if limit and len(history) > limit:
            # Return most recent N
            return history[-limit:]
        
        return history.copy()
    
    def clear_history(
        self,
        channel_id: str,
        sender_id: str,
        thread_id: str | None = None,
    ) -> None:
        """
        Clear history for session
        
        Args:
            channel_id: Channel ID
            sender_id: Sender ID
            thread_id: Optional thread ID
        """
        session_key = self._make_session_key(channel_id, sender_id, thread_id)
        
        if session_key in self._histories:
            del self._histories[session_key]
            logger.debug(f"Cleared history for session: {session_key}")
    
    def get_stats(self) -> dict[str, int]:
        """Get history statistics"""
        total_messages = sum(len(h) for h in self._histories.values())
        
        return {
            "sessions": len(self._histories),
            "total_messages": total_messages,
        }


# Global history instance
_global_history: Optional[MessageHistory] = None


def get_global_history() -> MessageHistory:
    """Get or create global history instance"""
    global _global_history
    
    if _global_history is None:
        _global_history = MessageHistory()
    
    return _global_history
