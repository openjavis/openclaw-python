"""Tests for ToolLoopOrchestrator"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from openclaw.agents.session import Session
from openclaw.agents.tool_loop import MAX_TOOL_ITERATIONS, ToolLoopOrchestrator, ToolResult
from openclaw.events import Event, EventType


@pytest.fixture
def mock_session():
    """Create a mock session"""
    session = Mock(spec=Session)
    session.session_id = "test-session-123"
    session.get_messages = Mock(return_value=[])
    session.add_user_message = Mock()
    session.add_assistant_message = Mock()
    session.add_tool_message = Mock()
    return session


@pytest.fixture
def mock_runtime():
    """Create a mock runtime"""
    runtime = Mock()
    runtime.provider_name = "test-provider"
    
    # Mock _stream_single_turn to return events
    async def mock_stream(*args, **kwargs):
        # Simulate text response
        yield Event(
            type=EventType.AGENT_TEXT,
            source="test",
            session_id="test-session-123",
            data={"delta": {"text": "Test response"}}
        )
        yield Event(
            type=EventType.AGENT_TURN_COMPLETE,
            source="test",
            session_id="test-session-123",
            data={}
        )
    
    runtime._stream_single_turn = Mock(side_effect=mock_stream)
    return runtime


@pytest.fixture
def mock_tools():
    """Create mock tools"""
    tool1 = Mock()
    tool1.name = "calculator"
    tool1.execute = AsyncMock(return_value="42")
    
    tool2 = Mock()
    tool2.name = "search"
    tool2.execute = AsyncMock(return_value="Found results")
    
    return [tool1, tool2]


@pytest.mark.asyncio
async def test_orchestrator_simple_text_response(mock_session, mock_runtime, mock_tools):
    """Test simple text response without tool calls"""
    orchestrator = ToolLoopOrchestrator(max_iterations=5)
    
    events = []
    async for event in orchestrator.execute_with_tools(
        session=mock_session,
        prompt="Hello",
        tools=mock_tools,
        runtime=mock_runtime,
    ):
        events.append(event)
    
    # Should have received events
    assert len(events) > 0
    
    # Should have added user message
    mock_session.add_user_message.assert_called_once_with("Hello", images=None)
    
    # Should have called runtime
    assert mock_runtime._stream_single_turn.called


@pytest.mark.asyncio
async def test_orchestrator_with_tool_calls(mock_session, mock_runtime, mock_tools):
    """Test orchestrator with tool calls"""
    # Mock runtime to return tool execution events
    async def mock_stream_with_tools(*args, **kwargs):
        is_followup = kwargs.get('is_followup', False)
        
        if not is_followup:
            # Initial call - return tool execution
            yield Event(
                type=EventType.TOOL_EXECUTION_START,
                source="test",
                session_id="test-session-123",
                data={"tool_call_id": "call_1", "tool_name": "calculator", "args": {"x": 2, "y": 2}}
            )
            yield Event(
                type=EventType.TOOL_EXECUTION_END,
                source="test",
                session_id="test-session-123",
                data={"tool_call_id": "call_1", "tool_name": "calculator", "success": True, "result": "4"}
            )
        else:
            # Follow-up call - return text response
            yield Event(
                type=EventType.AGENT_TEXT,
                source="test",
                session_id="test-session-123",
                data={"delta": {"text": "The answer is 4"}}
            )
    
    mock_runtime._stream_single_turn = Mock(side_effect=mock_stream_with_tools)
    
    orchestrator = ToolLoopOrchestrator(max_iterations=5)
    
    events = []
    async for event in orchestrator.execute_with_tools(
        session=mock_session,
        prompt="What is 2+2?",
        tools=mock_tools,
        runtime=mock_runtime,
    ):
        events.append(event)
    
    # Should have tool execution events
    tool_events = [e for e in events if hasattr(e, 'type') and 'TOOL' in str(e.type)]
    assert len(tool_events) > 0
    
    # Should have called runtime twice (initial + follow-up)
    assert mock_runtime._stream_single_turn.call_count == 2


@pytest.mark.asyncio
async def test_orchestrator_max_iterations(mock_session, mock_runtime, mock_tools):
    """Test that orchestrator stops at max iterations"""
    # Mock runtime to always return tool calls (infinite loop scenario)
    call_count = 0
    
    async def mock_infinite_tools(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        # Always return a tool call to simulate loop
        yield Event(
            type=EventType.TOOL_EXECUTION_START,
            source="test",
            session_id="test-session-123",
            data={"tool_call_id": f"call_{call_count}", "tool_name": "calculator", "args": {}}
        )
        yield Event(
            type=EventType.TOOL_EXECUTION_END,
            source="test",
            session_id="test-session-123",
            data={"tool_call_id": f"call_{call_count}", "tool_name": "calculator", "success": True, "result": "loop"}
        )
    
    mock_runtime._stream_single_turn = Mock(side_effect=mock_infinite_tools)
    
    orchestrator = ToolLoopOrchestrator(max_iterations=3)
    
    events = []
    async for event in orchestrator.execute_with_tools(
        session=mock_session,
        prompt="Test infinite loop",
        tools=mock_tools,
        runtime=mock_runtime,
    ):
        events.append(event)
    
    # Should have stopped at max iterations
    assert call_count <= 3
    
    # Should have a turn complete event indicating max iterations
    complete_events = [e for e in events if hasattr(e, 'type') and 'TURN_COMPLETE' in str(e.type)]
    assert len(complete_events) > 0


@pytest.mark.asyncio
async def test_orchestrator_loop_detection(mock_session, mock_runtime, mock_tools):
    """Test that orchestrator detects tool call loops in follow-up"""
    iteration = 0
    
    async def mock_loop_scenario(*args, **kwargs):
        nonlocal iteration
        is_followup = kwargs.get('is_followup', False)
        
        # Always return tool calls to simulate loop
        iteration += 1
        yield Event(
            type=EventType.TOOL_EXECUTION_START,
            source="test",
            session_id="test-session-123",
            data={"tool_call_id": f"call_{iteration}", "tool_name": "search", "args": {}}
        )
        yield Event(
            type=EventType.TOOL_EXECUTION_END,
            source="test",
            session_id="test-session-123",
            data={"tool_call_id": f"call_{iteration}", "tool_name": "search", "success": True, "result": "result"}
        )
    
    mock_runtime._stream_single_turn = Mock(side_effect=mock_loop_scenario)
    
    orchestrator = ToolLoopOrchestrator(max_iterations=5)
    
    events = []
    async for event in orchestrator.execute_with_tools(
        session=mock_session,
        prompt="Test loop detection",
        tools=mock_tools,
        runtime=mock_runtime,
    ):
        events.append(event)
    
    # Should have detected loop and stopped
    # Loop detection happens when follow-up (iteration > 1) also returns tool calls
    assert iteration >= 2  # At least initial + one follow-up with tools
    
    # Should have turn complete event
    complete_events = [e for e in events if hasattr(e, 'type') and 'TURN_COMPLETE' in str(e.type)]
    assert len(complete_events) > 0


@pytest.mark.asyncio
async def test_orchestrator_observer_notification(mock_session, mock_runtime, mock_tools):
    """Test that orchestrator notifies observers"""
    orchestrator = ToolLoopOrchestrator(max_iterations=5)
    
    received_events = []
    
    async def observer(event):
        received_events.append(event)
    
    orchestrator.add_observer(observer)
    
    async for event in orchestrator.execute_with_tools(
        session=mock_session,
        prompt="Test observers",
        tools=mock_tools,
        runtime=mock_runtime,
    ):
        pass
    
    # Observer should have received all events
    assert len(received_events) > 0


def test_orchestrator_max_iterations_constant():
    """Test that MAX_TOOL_ITERATIONS constant is defined"""
    assert MAX_TOOL_ITERATIONS == 5


def test_orchestrator_initialization():
    """Test orchestrator initialization"""
    orchestrator = ToolLoopOrchestrator(max_iterations=10)
    assert orchestrator.max_iterations == 10
    assert orchestrator._observers == []
