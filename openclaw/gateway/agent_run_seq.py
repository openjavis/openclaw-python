"""
Agent run sequence tracking - aligned with openclaw-ts agentRunSeq

Tracks event sequence numbers per run to detect gaps and ensure ordering.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class AgentRunSeqTracker:
    """
    Agent run sequence number tracker - aligned with openclaw-ts agentRunSeq
    
    Tracks the current sequence number for each run_id to:
    - Generate sequential event sequence numbers
    - Detect sequence gaps (missing events)
    - Ensure proper event ordering
    
    Thread-safe through async locks.
    """
    
    def __init__(self):
        self._seq: Dict[str, int] = {}  # runId -> current sequence number
        self._lock = asyncio.Lock()
    
    async def get_next_seq(self, run_id: str) -> int:
        """
        Get next sequence number for a run
        
        Args:
            run_id: Run ID
            
        Returns:
            Next sequence number (0-indexed)
        """
        async with self._lock:
            current = self._seq.get(run_id, -1)
            next_seq = current + 1
            self._seq[run_id] = next_seq
            return next_seq
    
    async def check_gap(self, run_id: str, received_seq: int) -> int | None:
        """
        Check for sequence number gap - aligned with openclaw-ts
        
        Used to detect missing events when receiving events from external source.
        
        Args:
            run_id: Run ID
            received_seq: Received sequence number
            
        Returns:
            Expected sequence number if gap detected, None otherwise
        """
        async with self._lock:
            expected = self._seq.get(run_id, 0)
            
            if received_seq != expected:
                logger.warning(
                    f"Sequence gap detected for {run_id}: "
                    f"expected {expected}, got {received_seq}"
                )
                # Update to received (accepting the gap)
                self._seq[run_id] = received_seq
                return expected
            
            # No gap, update sequence
            self._seq[run_id] = received_seq
            return None
    
    async def get_current_seq(self, run_id: str) -> int:
        """
        Get current sequence number for a run
        
        Args:
            run_id: Run ID
            
        Returns:
            Current sequence number (-1 if not started)
        """
        async with self._lock:
            return self._seq.get(run_id, -1)
    
    async def reset(self, run_id: str) -> None:
        """
        Reset sequence for a run (when it completes)
        
        Args:
            run_id: Run ID to reset
        """
        async with self._lock:
            if run_id in self._seq:
                del self._seq[run_id]
                logger.debug(f"Reset sequence for run {run_id}")
    
    async def cleanup(self, max_entries: int = 1000) -> int:
        """
        Cleanup old entries if too many are tracked
        
        Args:
            max_entries: Maximum entries to keep
            
        Returns:
            Number of entries removed
        """
        async with self._lock:
            if len(self._seq) <= max_entries:
                return 0
            
            # Sort by sequence number and keep most recent
            sorted_items = sorted(self._seq.items(), key=lambda x: x[1], reverse=True)
            to_keep = dict(sorted_items[:max_entries])
            
            removed = len(self._seq) - len(to_keep)
            self._seq = to_keep
            
            logger.info(f"Cleaned up {removed} sequence entries")
            return removed
