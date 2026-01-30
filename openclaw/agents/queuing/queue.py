"""
Queue manager for session and global lanes
"""

import hashlib
import logging
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from .lane import Lane

logger = logging.getLogger(__name__)

T = TypeVar("T")


class QueueManager:
    """
    Manage session and global execution lanes

    Features:
    - Per-session sequential execution (prevents conflicts)
    - Global concurrent limit (resource management)
    - Automatic lane creation and cleanup
    """

    def __init__(self, max_concurrent_per_session: int = 1, max_concurrent_global: int = 10):
        """
        Initialize queue manager

        Args:
            max_concurrent_per_session: Max concurrent per session
            max_concurrent_global: Max concurrent globally
        """
        self.max_concurrent_per_session = max_concurrent_per_session
        self.max_concurrent_global = max_concurrent_global

        self._session_lanes: dict[str, Lane] = {}
        self._global_lane = Lane("global", max_concurrent_global)

    def get_session_lane(self, session_id: str) -> Lane:
        """
        Get or create lane for session

        Args:
            session_id: Session identifier

        Returns:
            Lane for this session
        """
        if session_id not in self._session_lanes:
            # Create deterministic lane name
            lane_name = f"session-{self._hash_session_id(session_id)}"
            self._session_lanes[session_id] = Lane(lane_name, self.max_concurrent_per_session)
            logger.debug(f"Created lane for session: {session_id}")

        return self._session_lanes[session_id]

    def get_global_lane(self) -> Lane:
        """Get global lane"""
        return self._global_lane

    async def enqueue_session(
        self,
        session_id: str,
        task: Callable[[], Coroutine[Any, Any, T]],
        timeout: float | None = None,
    ) -> T:
        """
        Enqueue task in session lane

        Args:
            session_id: Session identifier
            task: Async function to execute
            timeout: Optional timeout

        Returns:
            Task result
        """
        lane = self.get_session_lane(session_id)
        return await lane.enqueue(task, timeout)

    async def enqueue_global(
        self, task: Callable[[], Coroutine[Any, Any, T]], timeout: float | None = None
    ) -> T:
        """
        Enqueue task in global lane

        Args:
            task: Async function to execute
            timeout: Optional timeout

        Returns:
            Task result
        """
        return await self._global_lane.enqueue(task, timeout)

    async def enqueue_both(
        self,
        session_id: str,
        task: Callable[[], Coroutine[Any, Any, T]],
        timeout: float | None = None,
    ) -> T:
        """
        Enqueue task in both session and global lanes

        This ensures:
        1. Only one request per session at a time
        2. Global concurrency limit is respected

        Args:
            session_id: Session identifier
            task: Async function to execute
            timeout: Optional timeout

        Returns:
            Task result
        """
        session_lane = self.get_session_lane(session_id)

        # Enqueue in session lane, which then enqueues in global
        async def wrapped_task():
            return await self._global_lane.enqueue(task, timeout)

        return await session_lane.enqueue(wrapped_task, timeout)

    async def cleanup_session(self, session_id: str) -> None:
        """
        Clean up session lane

        Args:
            session_id: Session to clean up
        """
        if session_id in self._session_lanes:
            lane = self._session_lanes[session_id]
            await lane.stop()
            del self._session_lanes[session_id]
            logger.debug(f"Cleaned up lane for session: {session_id}")

    def get_stats(self) -> dict:
        """Get queue manager statistics"""
        return {
            "global": self._global_lane.get_stats(),
            "sessions": {sid: lane.get_stats() for sid, lane in self._session_lanes.items()},
            "total_sessions": len(self._session_lanes),
        }

    def _hash_session_id(self, session_id: str) -> str:
        """Create short hash of session ID"""
        return hashlib.md5(session_id.encode()).hexdigest()[:8]
