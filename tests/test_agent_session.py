"""Tests for AgentSession"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from openclaw.agents.agent_session import AgentSession
from openclaw.agents.session import Session
from openclaw.events import Event, EventType


@pytest.fixture
def mock_session():
    """Create a mock session"""
    session = Mock(spec=Session)
    session.session_id = "test-session-456"
    session.get_messages = Mock(return_value=[])
    session.add_user_message = Mock()
    session.add_assistant_message = Mock()
    session.clear_messages = Mock()
    return session


@pytest.fixture
def mock_runtime():
    """Create a mock runtime"""
    runtime = Mock()
    runtime.provider_name = "test-provider"
    runtime._stream_single_turn = AsyncMock()
    return runtime


@pytest.fixture
def mock_tools():
    """Create mock tools"""
    tool = Mock()
    tool.name = "test_tool"
    tool.execute = AsyncMock(return_value="test result")
    return [tool]


def test_agent_session_initialization(mock_session, mock_runtime, mock_tools):
    """Test AgentSession initialization"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
        system_prompt="Test prompt",
        max_iterations=10,
        max_tokens=2048,
    )
    
    assert agent_session.session == mock_session
    assert agent_session.runtime == mock_runtime
    assert agent_session.tools == mock_tools
    assert agent_session.system_prompt == "Test prompt"
    assert agent_session.max_tokens == 2048
    assert agent_session._orchestrator is not None
    assert agent_session._subscribers == []
    assert agent_session.is_streaming == False


def test_agent_session_properties(mock_session, mock_runtime, mock_tools):
    """Test AgentSession properties"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    assert agent_session.session_id == "test-session-456"
    assert agent_session.is_streaming == False
    
    mock_session.get_messages.return_value = [Mock(), Mock(), Mock()]
    assert agent_session.get_message_count() == 3


def test_agent_session_subscribe(mock_session, mock_runtime, mock_tools):
    """Test event subscription"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    handler_called = []
    
    def event_handler(event):
        handler_called.append(event)
    
    # Subscribe
    unsubscribe = agent_session.subscribe(event_handler)
    assert len(agent_session._subscribers) == 1
    
    # Unsubscribe
    unsubscribe()
    assert len(agent_session._subscribers) == 0


@pytest.mark.asyncio
async def test_agent_session_prompt(mock_session, mock_runtime, mock_tools):
    """Test prompt() method"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    # Mock orchestrator to avoid actual execution
    with patch.object(agent_session._orchestrator, 'execute_with_tools') as mock_execute:
        async def mock_events(*args, **kwargs):
            yield Event(
                type=EventType.AGENT_TEXT,
                source="test",
                session_id="test-session-456",
                data={"delta": {"text": "Test"}}
            )
        
        mock_execute.return_value = mock_events()
        
        # Call prompt
        await agent_session.prompt("Test prompt")
        
        # Should have called orchestrator
        mock_execute.assert_called_once()
        
        # Check arguments
        call_args = mock_execute.call_args
        assert call_args.kwargs['session'] == mock_session
        assert call_args.kwargs['prompt'] == "Test prompt"
        assert call_args.kwargs['tools'] == mock_tools
        assert call_args.kwargs['runtime'] == mock_runtime


@pytest.mark.asyncio
async def test_agent_session_prompt_with_images(mock_session, mock_runtime, mock_tools):
    """Test prompt() with images"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    with patch.object(agent_session._orchestrator, 'execute_with_tools') as mock_execute:
        async def mock_events(*args, **kwargs):
            yield Event(
                type=EventType.AGENT_TEXT,
                source="test",
                session_id="test-session-456",
                data={"delta": {"text": "Test"}}
            )
        
        mock_execute.return_value = mock_events()
        
        # Call prompt with images
        images = ["image1.jpg", "image2.jpg"]
        await agent_session.prompt("Describe images", images=images)
        
        # Check images were passed
        call_args = mock_execute.call_args
        assert call_args.kwargs['images'] == images


@pytest.mark.asyncio
async def test_agent_session_streaming_state(mock_session, mock_runtime, mock_tools):
    """Test is_streaming state during prompt execution"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    # Initially not streaming
    assert agent_session.is_streaming == False
    
    streaming_states = []
    
    async def check_streaming():
        await asyncio.sleep(0.01)
        streaming_states.append(agent_session.is_streaming)
    
    with patch.object(agent_session._orchestrator, 'execute_with_tools') as mock_execute:
        async def mock_events(*args, **kwargs):
            # Record streaming state during execution
            streaming_states.append(agent_session.is_streaming)
            yield Event(
                type=EventType.AGENT_TEXT,
                source="test",
                session_id="test-session-456",
                data={"delta": {"text": "Test"}}
            )
        
        mock_execute.return_value = mock_events()
        
        # Start prompt execution
        await agent_session.prompt("Test")
    
    # Should have been streaming during execution
    assert True in streaming_states
    
    # Should not be streaming after completion
    assert agent_session.is_streaming == False


@pytest.mark.asyncio
async def test_agent_session_event_forwarding(mock_session, mock_runtime, mock_tools):
    """Test that events are forwarded to subscribers"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    received_events = []
    
    def handler(event):
        received_events.append(event)
    
    agent_session.subscribe(handler)
    
    with patch.object(agent_session._orchestrator, 'execute_with_tools') as mock_execute:
        async def mock_events(*args, **kwargs):
            yield Event(
                type=EventType.AGENT_TEXT,
                source="test",
                session_id="test-session-456",
                data={"delta": {"text": "Event 1"}}
            )
            yield Event(
                type=EventType.AGENT_TEXT,
                source="test",
                session_id="test-session-456",
                data={"delta": {"text": "Event 2"}}
            )
        
        mock_execute.return_value = mock_events()
        
        await agent_session.prompt("Test")
    
    # Should have received all events
    assert len(received_events) == 2


def test_agent_session_reset(mock_session, mock_runtime, mock_tools):
    """Test session reset"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    agent_session.reset()
    
    # Should have cleared messages
    mock_session.clear_messages.assert_called_once()


def test_agent_session_repr(mock_session, mock_runtime, mock_tools):
    """Test __repr__"""
    agent_session = AgentSession(
        session=mock_session,
        runtime=mock_runtime,
        tools=mock_tools,
    )
    
    repr_str = repr(agent_session)
    assert "AgentSession" in repr_str
    assert "test-session-456" in repr_str or "test-ses" in repr_str  # Truncated ID
    assert "tools=1" in repr_str
    assert "streaming=False" in repr_str
