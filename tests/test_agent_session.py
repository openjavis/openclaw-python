"""Tests for the pi_coding_agent-backed AgentSession adapter."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from openclaw.agents.agent_session import AgentSession, HookRegistry
from openclaw.events import Event, EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_pi_session():
    """Mock pi_coding_agent.AgentSession."""
    pi = MagicMock()
    pi.session_id = "test-session-456"
    pi.prompt = AsyncMock()
    pi.abort = AsyncMock()
    pi._all_tools = []
    pi._agent = MagicMock()
    pi.subscribe = MagicMock(return_value=lambda: None)
    return pi


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def test_agent_session_initialization():
    """Test AgentSession construction with minimal args."""
    session = AgentSession(
        session_key="agent:main:default",
        cwd="/workspace",
        model="google/gemini-2.0-flash",
        system_prompt="You are openclaw.",
    )
    assert session.session_key == "agent:main:default"
    assert session.cwd == "/workspace"
    assert session._model_str == "google/gemini-2.0-flash"
    assert session._system_prompt == "You are openclaw."
    assert session._subscribers == []
    assert session.is_streaming is False
    assert session._pi_session is None


def test_agent_session_legacy_params_accepted():
    """Legacy params session= runtime= tools= should not raise."""
    old_session = Mock()
    old_session.session_id = "legacy-session-id"
    old_runtime = Mock()
    tool = Mock()
    tool.name = "test_tool"

    agent_session = AgentSession(
        session=old_session,
        runtime=old_runtime,
        tools=[tool],
        system_prompt="Test prompt",
        max_iterations=10,
        max_tokens=2048,
    )
    assert agent_session._extra_tools == [tool]
    assert agent_session._external_session_id == "legacy-session-id"
    assert agent_session._system_prompt == "Test prompt"
    assert agent_session.is_streaming is False


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def test_session_id_before_pi_session():
    """session_id returns external ID before pi session is created."""
    s = AgentSession(session_id="my-ext-id")
    assert s.session_id == "my-ext-id"


def test_session_id_after_pi_session(mock_pi_session):
    """session_id delegates to pi session once created."""
    s = AgentSession(session_id="ext-id")
    s._pi_session = mock_pi_session
    assert s.session_id == "test-session-456"


def test_is_streaming_default():
    s = AgentSession()
    assert s.is_streaming is False


# ---------------------------------------------------------------------------
# Subscribe / unsubscribe
# ---------------------------------------------------------------------------

def test_subscribe_returns_unsubscribe():
    session = AgentSession()
    handler_called = []

    def handler(event):
        handler_called.append(event)

    unsub = session.subscribe(handler)
    assert len(session._subscribers) == 1

    unsub()
    assert len(session._subscribers) == 0


def test_subscribe_multiple_handlers():
    session = AgentSession()
    h1 = Mock()
    h2 = Mock()
    u1 = session.subscribe(h1)
    u2 = session.subscribe(h2)
    assert len(session._subscribers) == 2
    u1()
    assert len(session._subscribers) == 1
    u2()
    assert len(session._subscribers) == 0


# ---------------------------------------------------------------------------
# prompt() — happy path via mock pi session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_calls_pi_session(mock_pi_session):
    """prompt() should call pi_session.prompt() with the text."""
    s = AgentSession(session_id="test")
    s._pi_session = mock_pi_session
    mock_pi_session.subscribe = MagicMock(return_value=lambda: None)

    with patch.object(s, "_get_pi_session", return_value=mock_pi_session):
        await s.prompt("Hello world")

    mock_pi_session.prompt.assert_awaited_once_with("Hello world")


@pytest.mark.asyncio
async def test_prompt_sets_is_streaming(mock_pi_session):
    """is_streaming should be True during prompt and False after."""
    s = AgentSession(session_id="test")
    streaming_states: list[bool] = []

    async def fake_prompt(text):
        streaming_states.append(s.is_streaming)

    mock_pi_session.prompt = fake_prompt
    mock_pi_session.subscribe = MagicMock(return_value=lambda: None)

    with patch.object(s, "_get_pi_session", return_value=mock_pi_session):
        await s.prompt("Test")

    assert True in streaming_states
    assert s.is_streaming is False


@pytest.mark.asyncio
async def test_prompt_emits_error_event_on_failure():
    """prompt() should emit an ERROR event when pi session raises."""
    s = AgentSession(session_id="test")
    received: list[Event] = []
    s.subscribe(received.append)

    bad_pi = MagicMock()
    bad_pi.session_id = "test"
    bad_pi.subscribe = MagicMock(return_value=lambda: None)
    bad_pi.prompt = AsyncMock(side_effect=RuntimeError("boom"))

    with patch.object(s, "_get_pi_session", return_value=bad_pi):
        await s.prompt("Fail")

    assert len(received) == 1
    assert received[0].type == EventType.ERROR
    assert "boom" in received[0].data["message"]


# ---------------------------------------------------------------------------
# abort() and reset()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_abort_delegates_to_pi_session(mock_pi_session):
    s = AgentSession(session_id="test")
    s._pi_session = mock_pi_session
    await s.abort()
    mock_pi_session.abort.assert_awaited_once()


@pytest.mark.asyncio
async def test_abort_no_op_when_no_pi_session():
    """abort() should not raise when pi session hasn't been created."""
    s = AgentSession(session_id="test")
    await s.abort()  # Should not raise


def test_reset_clears_pi_session(mock_pi_session):
    s = AgentSession(session_id="test")
    s._pi_session = mock_pi_session
    s.reset()
    assert s._pi_session is None


# ---------------------------------------------------------------------------
# HookRegistry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hook_registry_runs_hooks():
    reg = HookRegistry()
    log: list[str] = []

    def sync_hook(ctx: dict) -> dict:
        log.append("sync")
        return {"extra": 1}

    async def async_hook(ctx: dict) -> dict:
        log.append("async")
        return {"extra2": 2}

    reg.register("my_hook", sync_hook)
    reg.register("my_hook", async_hook)

    result = await reg.run("my_hook", {"initial": True})
    assert log == ["sync", "async"]
    assert result["extra"] == 1
    assert result["extra2"] == 2
    assert result["initial"] is True


@pytest.mark.asyncio
async def test_hook_registry_unregister():
    reg = HookRegistry()
    called = []
    fn = lambda ctx: called.append(1)
    reg.register("h", fn)
    reg.unregister("h", fn)
    await reg.run("h", {})
    assert called == []


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------

def test_agent_session_repr():
    s = AgentSession(session_key="agent:main:default", session_id="abc123def456")
    r = repr(s)
    assert "AgentSession" in r
    assert "streaming=False" in r
