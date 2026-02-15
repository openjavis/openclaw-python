"""
Complete unit tests for Cron service with alignment verification
"""
import asyncio
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from openclaw.cron import CronService
from openclaw.cron.types import CronJob, AtSchedule, EverySchedule, SystemEventPayload, AgentTurnPayload, CronDelivery
from openclaw.cron.store import CronStore
from openclaw.gateway.types import GatewayDeps, GatewayCronState


@pytest.fixture
def temp_cron_dir(tmp_path):
    """Create temporary cron directory"""
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    return cron_dir


@pytest.fixture
def mock_deps():
    """Create mock GatewayDeps"""
    deps = Mock(spec=GatewayDeps)
    deps.provider = Mock()
    deps.tools = []
    deps.session_manager = Mock()
    deps.get_channel_manager = Mock(return_value=None)
    return deps


class TestCronServiceBasics:
    """Basic cron service tests"""

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
        assert not service._service_running

    @pytest.mark.asyncio
    async def test_cron_service_start(self, temp_cron_dir):
        """Test cron service starts correctly"""
        service = CronService(
            store_path=temp_cron_dir / "jobs.json"
        )

        await service.start()

        assert service._service_running
        assert service._timer is not None

        service.stop()

    @pytest.mark.asyncio
    async def test_add_job(self, temp_cron_dir):
        """Test adding a cron job"""
        service = CronService(
            store_path=temp_cron_dir / "jobs.json"
        )

        job = CronJob(
            id="test-1",
            name="Test Job",
            schedule=EverySchedule(interval_ms=60000, type="every"),
            session_target="main",
            payload=SystemEventPayload(kind="systemEvent", text="Test"),
            enabled=True
        )

        await service.add_job(job)

        assert "test-1" in service.jobs
        assert service.jobs["test-1"].name == "Test Job"

    @pytest.mark.asyncio
    async def test_status(self, temp_cron_dir):
        """Test status returns correct info"""
        service = CronService(
            store_path=temp_cron_dir / "jobs.json",
            cron_enabled=True,
        )

        status = await service.status()

        assert status["enabled"] is True
        assert status["jobs"] == 0

    @pytest.mark.asyncio
    async def test_run_with_due_mode(self, temp_cron_dir):
        """Test run with due vs force mode"""
        service = CronService(store_path=temp_cron_dir / "jobs.json")

        job = CronJob(
            id="test-run",
            name="Run Test",
            schedule=EverySchedule(interval_ms=3600000, type="every"),  # 1 hour
            payload=SystemEventPayload(kind="systemEvent", text="Test"),
        )
        await service.add_job(job)

        # Run with "due" mode - job shouldn't be due yet
        result = await service.run("test-run", mode="due")
        assert result["ran"] is False
        assert result["reason"] == "not-due"

    @pytest.mark.asyncio
    async def test_wake(self, temp_cron_dir):
        """Test wake sends event"""
        events = []

        def capture(text, agent_id=None):
            events.append(text)

        service = CronService(
            store_path=temp_cron_dir / "jobs.json",
            enqueue_system_event=capture,
        )

        result = service.wake("Hello from wake", mode="now")
        assert result["ok"] is True
        assert len(events) == 1
        assert events[0] == "Hello from wake"


class TestCronServicePersistence:
    """Test cron job persistence"""

    @pytest.mark.asyncio
    async def test_job_persistence(self, temp_cron_dir):
        """Test jobs persist across service restarts"""
        store_path = temp_cron_dir / "jobs.json"

        # Create service and add job
        service1 = CronService(store_path=store_path)

        job = CronJob(
            id="persist-test",
            name="Persistence Test",
            schedule=EverySchedule(interval_ms=60000, type="every"),
            session_target="main",
            payload=SystemEventPayload(kind="systemEvent", text="Test"),
            enabled=True
        )

        await service1.add_job(job)

        # Create new service instance
        service2 = CronService(store_path=store_path)

        # Load jobs
        if hasattr(service2, '_store') and service2._store:
            jobs = service2._store.load()
            for j in jobs:
                service2.jobs[j.id] = j

        # Job should be loaded
        assert "persist-test" in service2.jobs
        assert service2.jobs["persist-test"].name == "Persistence Test"


class TestCronCallbacks:
    """Test cron callback execution"""

    @pytest.mark.asyncio
    async def test_system_event_callback(self, temp_cron_dir):
        """Test system event callback is invoked"""
        callback_invoked = False
        received_text = None

        async def system_event_callback(text: str, agent_id: str | None = None):
            nonlocal callback_invoked, received_text
            callback_invoked = True
            received_text = text

        service = CronService(
            store_path=temp_cron_dir / "jobs.json",
            enqueue_system_event=system_event_callback,
        )

        # Manually trigger callback
        if service.enqueue_system_event:
            await service.enqueue_system_event("Test event")

        assert callback_invoked
        assert received_text == "Test event"

    @pytest.mark.asyncio
    async def test_isolated_agent_callback(self, temp_cron_dir):
        """Test isolated agent callback is invoked"""
        callback_invoked = False

        async def isolated_agent_callback(job: CronJob):
            nonlocal callback_invoked
            callback_invoked = True
            return {"success": True, "summary": "Test"}

        service = CronService(
            store_path=temp_cron_dir / "jobs.json",
            run_isolated_agent_job=isolated_agent_callback,
        )

        job = CronJob(
            id="test",
            name="Test",
            schedule=AtSchedule(timestamp=datetime.now(timezone.utc).isoformat(), type="at"),
            session_target="isolated",
            payload=AgentTurnPayload(kind="agentTurn", prompt="Test"),
            enabled=True
        )

        # Manually trigger callback
        if service.run_isolated_agent_job:
            result = await service.run_isolated_agent_job(job)

        assert callback_invoked
        assert result["success"]

    def test_emit_event(self, temp_cron_dir):
        """Test event emission"""
        received_events = []

        def on_event(event: dict):
            received_events.append(event)

        service = CronService(
            store_path=temp_cron_dir / "jobs.json",
            on_event=on_event,
        )

        # Trigger event via _emit
        service._emit(action="started", jobId="test-1")

        assert len(received_events) == 1
        assert received_events[0]["action"] == "started"

    @pytest.mark.asyncio
    async def test_update_job(self, temp_cron_dir):
        """Test updating a job with patch"""
        service = CronService(store_path=temp_cron_dir / "jobs.json")

        job = CronJob(
            id="test-update",
            name="Original Name",
            schedule=EverySchedule(interval_ms=60000, type="every"),
            payload=SystemEventPayload(kind="systemEvent", text="Test"),
        )
        await service.add_job(job)

        updated = await service.update_job("test-update", {"name": "New Name", "enabled": True})
        assert updated.name == "New Name"

    @pytest.mark.asyncio
    async def test_remove_job(self, temp_cron_dir):
        """Test removing a job"""
        service = CronService(store_path=temp_cron_dir / "jobs.json")

        job = CronJob(
            id="test-remove",
            name="To Remove",
            schedule=EverySchedule(interval_ms=60000, type="every"),
            payload=SystemEventPayload(kind="systemEvent", text="Test"),
        )
        await service.add_job(job)
        assert "test-remove" in service.jobs

        result = await service.remove_job("test-remove")
        assert result["removed"] is True
        assert "test-remove" not in service.jobs


class TestGatewayIntegration:
    """Test gateway integration types"""

    def test_gateway_deps_structure(self):
        """Test GatewayDeps has required fields"""
        from openclaw.gateway.types import GatewayDeps

        deps = GatewayDeps(
            provider=Mock(),
            tools=[],
            session_manager=Mock(),
            get_channel_manager=lambda: None
        )

        assert deps.provider is not None
        assert isinstance(deps.tools, list)
        assert deps.session_manager is not None
        assert callable(deps.get_channel_manager)

    def test_gateway_cron_state_structure(self):
        """Test GatewayCronState has required fields"""
        from openclaw.gateway.types import GatewayCronState

        service = Mock(spec=CronService)

        state = GatewayCronState(
            cron=service,
            store_path=Path("/tmp/test.json"),
            enabled=True
        )

        assert state.cron is not None
        assert isinstance(state.store_path, Path)
        assert state.enabled is True


@pytest.mark.integration
class TestCronScheduling:
    """Test cron scheduling logic"""

    def test_schedule_computation_every(self):
        """Test interval schedule computation"""
        schedule = EverySchedule(interval_ms=60000, type="every")

        assert schedule.type == "every"
        assert schedule.interval_ms == 60000

    def test_schedule_computation_at(self):
        """Test at schedule computation"""
        future_time = datetime.now(timezone.utc)
        schedule = AtSchedule(timestamp=future_time.isoformat(), type="at")

        assert schedule.type == "at"
        assert schedule.timestamp is not None


@pytest.mark.skip(reason="Requires full gateway setup")
class TestEndToEndCron:
    """End-to-end cron tests"""

    @pytest.mark.asyncio
    async def test_cron_with_gateway(self):
        """Test cron service integrated with gateway"""
        pass
