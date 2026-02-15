"""
Chat run state management - aligned with openclaw-ts server-chat.ts

Manages queuing of chat runs per session to ensure:
- Only one chat run per session at a time
- Proper sequencing of concurrent requests
- Delta debouncing for smooth streaming
"""
from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

# Delta debounce delay - aligned with openclaw-ts
DELTA_DEBOUNCE_MS = 150  # 150ms debounce for smoother streaming


@dataclass
class ChatRunEntry:
    """
    Chat run queue entry - aligned with openclaw-ts ChatRunEntry
    
    Tracks a single chat request through its lifecycle
    """
    run_id: str
    user_id: str
    session_id: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None


class ChatRunRegistry:
    """
    Chat run queue registry - aligned with openclaw-ts ChatRunRegistry
    
    Ensures same session's multiple requests are queued and processed sequentially.
    Prevents race conditions and ensures message ordering.
    """
    
    def __init__(self):
        self._queues: dict[str, list[ChatRunEntry]] = {}
        self._lock = asyncio.Lock()
    
    async def enqueue(self, session_id: str, entry: ChatRunEntry) -> None:
        """
        Add a run to the queue for this session
        
        Args:
            session_id: Session ID
            entry: Chat run entry to queue
        """
        async with self._lock:
            if session_id not in self._queues:
                self._queues[session_id] = []
            self._queues[session_id].append(entry)
            logger.debug(f"Enqueued run {entry.run_id} for session {session_id}")
    
    async def get_current(self, session_id: str) -> ChatRunEntry | None:
        """
        Get currently running entry for this session
        
        Args:
            session_id: Session ID
            
        Returns:
            Currently running entry, or None if no run is active
        """
        async with self._lock:
            queue = self._queues.get(session_id, [])
            for entry in queue:
                if entry.status == "running":
                    return entry
            return None
    
    async def get_next_pending(self, session_id: str) -> ChatRunEntry | None:
        """
        Get next pending entry for this session
        
        Args:
            session_id: Session ID
            
        Returns:
            Next pending entry, or None if queue is empty
        """
        async with self._lock:
            queue = self._queues.get(session_id, [])
            for entry in queue:
                if entry.status == "pending":
                    return entry
            return None
    
    async def mark_running(self, run_id: str) -> None:
        """
        Mark a run as running
        
        Args:
            run_id: Run ID to mark
        """
        async with self._lock:
            entry = self._find_entry(run_id)
            if entry:
                entry.status = "running"
                entry.started_at = time.time()
                logger.debug(f"Run {run_id} started")
    
    async def mark_completed(self, run_id: str, error: str | None = None) -> None:
        """
        Mark a run as completed and remove from queue
        
        Args:
            run_id: Run ID to mark
            error: Error message if failed
        """
        async with self._lock:
            entry = self._find_entry(run_id)
            if entry:
                entry.status = "failed" if error else "completed"
                entry.completed_at = time.time()
                entry.error = error
                
                # Remove from queue
                if entry.sessionId in self._queues:
                    self._queues[entry.sessionId] = [
                        e for e in self._queues[entry.sessionId] 
                        if e.run_id != run_id
                    ]
                    
                    # Clean up empty queues
                    if not self._queues[entry.sessionId]:
                        del self._queues[entry.sessionId]
                
                logger.debug(f"Run {run_id} completed (error={error})")
    
    async def abort_run(self, run_id: str) -> None:
        """
        Abort a running chat run
        
        Args:
            run_id: Run ID to abort
        """
        await self.mark_completed(run_id, error="aborted")
    
    async def get_queue_size(self, session_id: str) -> int:
        """
        Get queue size for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            Number of pending/running entries
        """
        async with self._lock:
            return len(self._queues.get(session_id, []))
    
    def _find_entry(self, run_id: str) -> ChatRunEntry | None:
        """Find entry by run_id across all queues (must hold lock)"""
        for queue in self._queues.values():
            for entry in queue:
                if entry.run_id == run_id:
                    return entry
        return None


@dataclass
class ChatRunState:
    """
    Chat run state container - aligned with openclaw-ts ChatRunState
    
    Combines:
    - registry: Queue management
    - buffers: Accumulated text for streaming
    - delta_sent_at: Debounce timestamps
    - aborted_runs: Tracking of aborted runs
    """
    registry: ChatRunRegistry = field(default_factory=ChatRunRegistry)
    buffers: dict[str, str] = field(default_factory=dict)  # runId -> accumulated text
    delta_sent_at: dict[str, float] = field(default_factory=dict)  # runId -> timestamp (ms)
    aborted_runs: dict[str, float] = field(default_factory=dict)  # runId -> abort timestamp (ms)


async def should_send_delta(
    run_id: str,
    state: ChatRunState,
    force: bool = False
) -> bool:
    """
    Determine if delta should be sent based on debounce timing - aligned with openclaw-ts
    
    Args:
        run_id: Run ID
        state: Chat run state
        force: Force sending (bypass debounce)
        
    Returns:
        True if delta should be sent now
    """
    if force:
        return True
    
    last_sent = state.delta_sent_at.get(run_id, 0)
    now = time.time() * 1000  # Convert to milliseconds
    
    return (now - last_sent) >= DELTA_DEBOUNCE_MS


def mark_delta_sent(run_id: str, state: ChatRunState) -> None:
    """
    Mark delta as sent for debounce tracking
    
    Args:
        run_id: Run ID
        state: Chat run state
    """
    state.delta_sent_at[run_id] = time.time() * 1000  # milliseconds


def append_to_buffer(run_id: str, text: str, state: ChatRunState) -> str:
    """
    Append text to buffer and return full accumulated text
    
    Args:
        run_id: Run ID
        text: Text to append
        state: Chat run state
        
    Returns:
        Full accumulated text
    """
    if run_id not in state.buffers:
        state.buffers[run_id] = ""
    
    state.buffers[run_id] += text
    return state.buffers[run_id]


def get_buffer(run_id: str, state: ChatRunState) -> str:
    """
    Get accumulated text buffer
    
    Args:
        run_id: Run ID
        state: Chat run state
        
    Returns:
        Accumulated text (empty string if none)
    """
    return state.buffers.get(run_id, "")


def clear_buffer(run_id: str, state: ChatRunState) -> None:
    """
    Clear buffer for a run
    
    Args:
        run_id: Run ID
        state: Chat run state
    """
    if run_id in state.buffers:
        del state.buffers[run_id]
    if run_id in state.delta_sent_at:
        del state.delta_sent_at[run_id]


def mark_aborted(run_id: str, state: ChatRunState) -> None:
    """
    Mark a run as aborted
    
    Args:
        run_id: Run ID
        state: Chat run state
    """
    state.aborted_runs[run_id] = time.time() * 1000


def is_aborted(run_id: str, state: ChatRunState) -> bool:
    """
    Check if a run was aborted
    
    Args:
        run_id: Run ID
        state: Chat run state
        
    Returns:
        True if run was aborted
    """
    return run_id in state.aborted_runs


def cleanup_aborted_runs(state: ChatRunState, ttl_ms: int = 300_000) -> None:
    """
    Clean up old aborted run entries (5 minute TTL)
    
    Args:
        state: Chat run state
        ttl_ms: Time-to-live in milliseconds
    """
    now = time.time() * 1000
    expired = [
        run_id for run_id, ts in state.aborted_runs.items()
        if (now - ts) > ttl_ms
    ]
    for run_id in expired:
        del state.aborted_runs[run_id]
