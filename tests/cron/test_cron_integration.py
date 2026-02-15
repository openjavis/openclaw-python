"""
Integration tests for Cron service (aligned with TypeScript cron system)
"""
import asyncio
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from openclaw.cron import CronService
from openclaw.cron.types import CronJob, AtSchedule, EverySchedule, CronSchedule, SystemEventPayload, AgentTurnPayload
from openclaw.cron.store import CronStore


@pytest.fixture
def temp_cron_dir(tmp_path):
    """Create temporary cron directory"""
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    return cron_dir


@pytest.fixture
def cron_store(temp_cron_dir):
    """Create cron store"""
    store_path = temp_cron_dir / "jobs.json"
    return CronStore(store_path)


@pytest.fixture
def mock_session_manager():
    """Mock session manager"""
    manager = Mock()
    manager.get_or_create = Mock(return_value=Mock(
        add_system_message=Mock(),
        add_user_message=Mock(),
        add_assistant_message=Mock(),
    ))
    return manager


@pytest.fixture
def mock_provider():
    """Mock LLM provider"""
    provider = Mock()
    provider.generate = AsyncMock(return_value={
        "text": "Test response",
        "success": True
    })
    return provider


class TestCronServiceIntegration:
    """Integration tests for CronService"""

    def test_cron_service_initialization(self, temp_cron_dir):
        """Test cron service initializes correctly"""
        store_path = temp_cron_dir / "jobs.json"
        log_dir = temp_cron_dir / "logs"

        service = CronService(
            store_path=store_path,
            log_dir=log_dir,
        )

        assert service.store_path == store_path
        assert service.log_dir == log_dir
        assert len(service.jobs) == 0

    @pytest.mark.asyncio
    async def test_cron_job_persistence(self, cron_store, temp_cron_dir):
        """Test jobs persist across service restarts"""
        store_path = temp_cron_dir / "jobs.json"

        # Create service and add job
        service = CronService(store_path=store_path)

        job = CronJob(
            id="test-job",
            name="Test Job",
            schedule=EverySchedule(interval_ms=60000, type="every"),
            session_target="main",
            payload=SystemEventPayload(kind="systemEvent", text="Test event"),
            enabled=True
        )

        await service.add_job(job)

        # Create new service instance
        service2 = CronService(store_path=store_path)

        # Load jobs manually
        store2 = CronStore(store_path)
        jobs = store2.load()
        for j in jobs:
            service2.jobs[j.id] = j

        await service2.start()

        # Job should be loaded
        assert "test-job" in service2.jobs
        assert service2.jobs["test-job"].name == "Test Job"

        service2.stop()

    @pytest.mark.asyncio
    async def test_system_event_callback(self, temp_cron_dir, mock_session_manager):
        """Test system event callback is invoked"""
        callback_invoked = False
        event_text = None

        async def system_event_callback(text: str, agent_id: str | None = None):
            nonlocal callback_invoked, event_text
            callback_invoked = True
            event_text = text

        service = CronService(
            store_path=temp_cron_dir / "jobs.json",
            enqueue_system_event=system_event_callback,
        )

        # Manually trigger callback
        await service.enqueue_system_event("Test event")

        assert callback_invoked
        assert event_text == "Test event"

    @pytest.mark.asyncio
    async def test_isolated_agent_callback(self, temp_cron_dir, mock_provider):
        """Test isolated agent callback is invoked"""
        callback_invoked = False

        async def isolated_agent_callback(job: CronJob):
            nonlocal callback_invoked
            callback_invoked = True
            return {"success": True, "result": "Test"}

        service = CronService(
            store_path=temp_cron_dir / "jobs.json",
            run_isolated_agent_job=isolated_agent_callback,
        )

        job = CronJob(
            id="test-job",
            name="Test",
            schedule=AtSchedule(timestamp=datetime.now(timezone.utc).isoformat(), type="at"),
            session_target="isolated",
            payload=AgentTurnPayload(kind="agentTurn", prompt="Test"),
            enabled=True
        )

        # Manually trigger callback
        result = await service.run_isolated_agent_job(job)

        assert callback_invoked
        assert result["success"]

    def test_cron_schedule_computation_every(self):
        """Test interval schedule computation"""
        from openclaw.cron.schedule import compute_next_run

        schedule = EverySchedule(interval_ms=60000, type="every")

        now = datetime.now(timezone.utc)
        now_ms = int(now.timestamp() * 1000)
        next_run_ms = compute_next_run(schedule, now_ms)

        assert next_run_ms is not None
        assert next_run_ms > now_ms

    def test_cron_schedule_computation_cron(self):
        """Test cron expression schedule computation"""
        from openclaw.cron.schedule import compute_next_run

        # Every day at 9 AM
        schedule = CronSchedule(expression="0 9 * * *", timezone="UTC", type="cron")

        now = datetime.now(timezone.utc)
        now_ms = int(now.timestamp() * 1000)
        next_run_ms = compute_next_run(schedule, now_ms)

        assert next_run_ms is not None
        assert next_run_ms > now_ms


class TestCronStore:
    """Integration tests for CronStore"""

    def test_store_persistence(self, cron_store):
        """Test store persists jobs correctly"""
        job = CronJob(
            id="job-1",
            name="Test Job",
            schedule=EverySchedule(interval_ms=60000, type="every"),
            session_target="main",
            payload=SystemEventPayload(kind="systemEvent", text="Test"),
            enabled=True
        )

        jobs = [job]
        cron_store.save(jobs)

        loaded = cron_store.load()

        assert len(loaded) == 1
        assert loaded[0].id == "job-1"
        assert loaded[0].name == "Test Job"

    def test_store_migration(self, cron_store, temp_cron_dir):
        """Test store migrates legacy format if needed"""
        cron_store.migrate_if_needed()
        jobs = cron_store.load()
        assert isinstance(jobs, list)


class TestCronCLI:
    """Integration tests for Cron CLI"""

    @pytest.mark.skip(reason="Requires full CLI setup")
    def test_cron_add_command(self):
        pass

    @pytest.mark.skip(reason="Requires full CLI setup")
    def test_cron_list_command(self):
        pass

    @pytest.mark.skip(reason="Requires full CLI setup")
    def test_cron_remove_command(self):
        pass


@pytest.mark.integration
class TestCronEndToEnd:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires full gateway setup")
    async def test_cron_with_gateway(self):
        pass
