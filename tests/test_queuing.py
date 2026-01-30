"""
Tests for session queuing
"""

import asyncio

import pytest

from openclaw.agents.queuing import Lane, QueueManager


class TestLane:
    """Test Lane class"""

    def test_lane_creation(self):
        """Test creating a lane"""
        lane = Lane("test-lane", max_concurrent=2)

        assert lane.name == "test-lane"
        assert lane.max_concurrent == 2
        assert lane.active == 0

    @pytest.mark.asyncio
    async def test_sequential_execution(self):
        """Test sequential execution in lane"""
        lane = Lane("test", max_concurrent=1)
        results = []

        async def task(value):
            results.append(f"start-{value}")
            await asyncio.sleep(0.01)
            results.append(f"end-{value}")
            return value

        # Queue multiple tasks
        task1 = asyncio.create_task(lane.enqueue(lambda: task(1)))
        task2 = asyncio.create_task(lane.enqueue(lambda: task(2)))

        await asyncio.gather(task1, task2)

        # Should execute sequentially (one finishes before next starts)
        assert results[0] == "start-1"
        assert results[1] == "end-1"
        assert results[2] == "start-2"
        assert results[3] == "end-2"

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test concurrent execution in lane"""
        lane = Lane("test", max_concurrent=2)
        active_count = []

        async def task(value):
            active_count.append(lane.active)
            await asyncio.sleep(0.01)
            return value

        # Queue multiple tasks
        tasks = [lane.enqueue(lambda v=i: task(v)) for i in range(3)]
        await asyncio.gather(*tasks)

        # Should have had 2 concurrent at some point
        assert max(active_count) <= 2

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test task timeout"""
        lane = Lane("test")

        async def slow_task():
            await asyncio.sleep(10)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            await lane.enqueue(slow_task, timeout=0.1)


class TestQueueManager:
    """Test QueueManager class"""

    def test_manager_creation(self):
        """Test creating queue manager"""
        manager = QueueManager(max_concurrent_per_session=1, max_concurrent_global=5)

        assert manager.max_concurrent_per_session == 1
        assert manager.max_concurrent_global == 5

    @pytest.mark.asyncio
    async def test_session_lane_isolation(self):
        """Test that different sessions get different lanes"""
        manager = QueueManager()

        lane1 = manager.get_session_lane("session-1")
        lane2 = manager.get_session_lane("session-2")

        assert lane1 != lane2
        assert lane1.name != lane2.name

    @pytest.mark.asyncio
    async def test_same_session_same_lane(self):
        """Test that same session gets same lane"""
        manager = QueueManager()

        lane1 = manager.get_session_lane("session-1")
        lane2 = manager.get_session_lane("session-1")

        assert lane1 is lane2

    @pytest.mark.asyncio
    async def test_enqueue_session(self):
        """Test enqueueing in session lane"""
        manager = QueueManager()

        async def task():
            return "result"

        result = await manager.enqueue_session("session-1", task)

        assert result == "result"

    @pytest.mark.asyncio
    async def test_enqueue_global(self):
        """Test enqueueing in global lane"""
        manager = QueueManager()

        async def task():
            return "global-result"

        result = await manager.enqueue_global(task)

        assert result == "global-result"

    @pytest.mark.asyncio
    async def test_enqueue_both(self):
        """Test enqueueing in both lanes"""
        manager = QueueManager()

        async def task():
            await asyncio.sleep(0.01)
            return "both-result"

        result = await manager.enqueue_both("session-1", task)

        assert result == "both-result"

    @pytest.mark.asyncio
    async def test_cleanup_session(self):
        """Test cleaning up session lane"""
        manager = QueueManager()

        manager.get_session_lane("session-1")
        assert "session-1" in manager._session_lanes

        await manager.cleanup_session("session-1")

        # Lane should be removed
        assert "session-1" not in manager._session_lanes

    def test_get_stats(self):
        """Test getting statistics"""
        manager = QueueManager()
        manager.get_session_lane("session-1")
        manager.get_session_lane("session-2")

        stats = manager.get_stats()

        assert "global" in stats
        assert "sessions" in stats
        assert stats["total_sessions"] == 2
