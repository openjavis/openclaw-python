"""
Chat run state tracking for delta throttling and abort control.

This module tracks active chat runs to support:
- Delta throttling (150ms minimum between chat.delta events)
- Abort signal propagation
- Buffer management for text deltas

Matches openclaw/src/gateway/server-chat.ts ChatRunState logic.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
import asyncio
from typing import Any


@dataclass
class ChatRun:
    """Represents an active chat run"""
    
    run_id: str
    client_run_id: str
    session_key: str
    conn_id: str
    started_at: float
    buffer: list[str] = field(default_factory=list)  # Text deltas
    last_delta_at: float = 0


class ChatRunRegistry:
    """
    Registry of active chat runs for delta throttling and abort.
    
    This tracks all active chat runs across connections and provides:
    - Run lifecycle management (add/remove)
    - Abort signal management
    - Delta throttling support
    
    Usage:
        registry = ChatRunRegistry()
        
        # Register new run
        registry.add_run(
            run_id="run_123",
            client_run_id="client_456",
            session_key="agent:main:session",
            conn_id="conn_789"
        )
        
        # Get abort signal for cancellation
        abort_signal = registry.get_abort_signal("run_123")
        
        # Check throttling
        if registry.should_throttle_delta("run_123"):
            await asyncio.sleep(0.15)
        
        # Clean up on completion
        registry.remove_run("run_123")
    """
    
    # Minimum interval between delta events (150ms)
    DELTA_THROTTLE_MS = 150
    
    def __init__(self):
        """Initialize chat run registry"""
        self._runs: dict[str, ChatRun] = {}  # run_id -> ChatRun
        self._abort_controllers: dict[str, asyncio.Event] = {}  # run_id -> Event
    
    def add_run(
        self, 
        run_id: str, 
        client_run_id: str, 
        session_key: str, 
        conn_id: str
    ) -> None:
        """
        Register new chat run.
        
        Args:
            run_id: Server run ID
            client_run_id: Client-provided run ID
            session_key: Session key for this run
            conn_id: Connection ID
        """
        self._runs[run_id] = ChatRun(
            run_id=run_id,
            client_run_id=client_run_id,
            session_key=session_key,
            conn_id=conn_id,
            started_at=time.time(),
            buffer=[],
            last_delta_at=0
        )
        self._abort_controllers[run_id] = asyncio.Event()
    
    def remove_run(self, run_id: str) -> ChatRun | None:
        """
        Clean up completed run.
        
        Args:
            run_id: Run ID to remove
            
        Returns:
            Removed ChatRun if found, None otherwise
        """
        run = self._runs.pop(run_id, None)
        self._abort_controllers.pop(run_id, None)
        return run
    
    def get_run(self, run_id: str) -> ChatRun | None:
        """
        Get chat run by ID.
        
        Args:
            run_id: Run ID
            
        Returns:
            ChatRun if found, None otherwise
        """
        return self._runs.get(run_id)
    
    def get_abort_signal(self, run_id: str) -> asyncio.Event | None:
        """
        Get abort signal for run.
        
        Args:
            run_id: Run ID
            
        Returns:
            asyncio.Event that will be set when run should abort
        """
        return self._abort_controllers.get(run_id)
    
    def abort_run(self, run_id: str) -> bool:
        """
        Signal run to abort.
        
        Args:
            run_id: Run ID to abort
            
        Returns:
            True if run was found and signaled, False otherwise
        """
        abort_signal = self._abort_controllers.get(run_id)
        if abort_signal:
            abort_signal.set()
            return True
        return False
    
    def should_throttle_delta(self, run_id: str) -> bool:
        """
        Check if delta should be throttled.
        
        Args:
            run_id: Run ID
            
        Returns:
            True if caller should wait before sending delta
        """
        run = self._runs.get(run_id)
        if not run:
            return False
        
        if run.last_delta_at == 0:
            return False
        
        elapsed_ms = (time.time() - run.last_delta_at) * 1000
        return elapsed_ms < self.DELTA_THROTTLE_MS
    
    def mark_delta_sent(self, run_id: str) -> None:
        """
        Mark that a delta was just sent.
        
        Args:
            run_id: Run ID
        """
        run = self._runs.get(run_id)
        if run:
            run.last_delta_at = time.time()
    
    def append_to_buffer(self, run_id: str, text: str) -> None:
        """
        Append text to run buffer.
        
        Args:
            run_id: Run ID
            text: Text to append
        """
        run = self._runs.get(run_id)
        if run:
            run.buffer.append(text)
    
    def get_buffer(self, run_id: str) -> list[str]:
        """
        Get buffer contents.
        
        Args:
            run_id: Run ID
            
        Returns:
            List of text deltas in buffer
        """
        run = self._runs.get(run_id)
        return run.buffer if run else []
    
    def clear_buffer(self, run_id: str) -> None:
        """
        Clear run buffer.
        
        Args:
            run_id: Run ID
        """
        run = self._runs.get(run_id)
        if run:
            run.buffer.clear()
    
    def get_all_runs(self) -> dict[str, ChatRun]:
        """
        Get all active runs.
        
        Returns:
            Dictionary of run_id -> ChatRun
        """
        return self._runs.copy()
    
    def count(self) -> int:
        """Get number of active runs"""
        return len(self._runs)


__all__ = [
    "ChatRun",
    "ChatRunRegistry",
]
