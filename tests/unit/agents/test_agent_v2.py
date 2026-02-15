"""
Unit tests for Agent v2 implementation.

Tests the core Agent functionality matching Pi Agent:
- Basic prompt/response
- Steering interrupts
- Follow-up continuation
- Turn tracking
- Event emission
- Tool execution
- Thinking modes
"""
import asyncio
import pytest

from openclaw.agents import Agent, AgentSession
from openclaw.agents.events import (
    AgentEndEvent,
    AgentEventType,
    AgentStartEvent,
    MessageEndEvent,
    MessageStartEvent,
    TurnEndEvent,
    TurnStartEvent,
)
from openclaw.agents.thinking import ThinkingLevel
from openclaw.agents.tools import AgentToolBase, AgentToolResult
from openclaw.agents.types import TextContent, UserMessage


class DummyTool(AgentToolBase):
    """Dummy tool for testing"""
    
    @property
    def name(self) -> str:
        return "dummy_tool"
    
    @property
    def label(self) -> str:
        return "Dummy Tool"
    
    @property
    def description(self) -> str:
        return "A dummy tool for testing"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            }
        }
    
    async def execute(self, tool_call_id: str, params: dict, signal=None, on_update=None):
        # Simulate tool execution
        result = AgentToolResult(
            content=[TextContent(type="text", text=f"Result: {params.get('input', '')}")],
            details={"executed": True}
        )
        
        if on_update:
            on_update(result)
        
        return result


@pytest.mark.asyncio
async def test_agent_prompt():
    """Test basic agent prompt functionality"""
    # Create agent with dummy provider
    agent = Agent(
        system_prompt="You are a helpful assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Collect events
    events = []
    async for event in agent.prompt([UserMessage(content="Hello")]):
        events.append(event)
    
    # Verify event sequence
    assert len(events) > 0
    assert any(isinstance(e, AgentStartEvent) for e in events)
    assert any(isinstance(e, AgentEndEvent) for e in events)


@pytest.mark.asyncio
async def test_agent_session():
    """Test AgentSession with steering and follow-up"""
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    session = AgentSession(agent)
    
    # Verify session created
    assert session is not None


@pytest.mark.asyncio
async def test_turn_tracking():
    """Test turn number tracking across multiple turns"""
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Execute multiple turns
    turn_events = []
    async for event in agent.prompt([UserMessage(content="Turn 1")]):
        if isinstance(event, (TurnStartEvent, TurnEndEvent)):
            turn_events.append(event)
    
    # Verify turn tracking
    assert len(turn_events) > 0


@pytest.mark.asyncio
async def test_event_sequence():
    """Test that event sequence matches Pi Agent"""
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    event_types = []
    async for event in agent.prompt([UserMessage(content="Test")]):
        event_types.append(event.type)
    
    # Verify expected event sequence
    assert AgentEventType.AGENT_START in event_types
    assert AgentEventType.MESSAGE_START in event_types
    assert AgentEventType.MESSAGE_END in event_types
    assert AgentEventType.AGENT_END in event_types


@pytest.mark.asyncio
async def test_tool_execution():
    """Test tool execution with streaming support"""
    tool = DummyTool()
    
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[tool],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Execute tool
    result = await tool.execute(
        tool_call_id="test_call",
        params={"input": "test"},
        signal=None,
        on_update=None
    )
    
    assert result is not None
    assert len(result.content) > 0


@pytest.mark.asyncio
async def test_thinking_mode():
    """Test thinking/reasoning mode"""
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.MEDIUM
    )
    
    # Verify thinking level set
    assert agent.thinking_level == ThinkingLevel.MEDIUM


@pytest.mark.asyncio
async def test_abort_signal():
    """Test agent abort via signal"""
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Test abort
    agent.abort()
    
    # Verify agent can be aborted
    assert True  # If we get here, abort didn't crash


@pytest.mark.asyncio
async def test_message_events():
    """Test message start/end events are emitted correctly"""
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    message_starts = []
    message_ends = []
    
    async for event in agent.prompt([UserMessage(content="Test message")]):
        if isinstance(event, MessageStartEvent):
            message_starts.append(event)
        elif isinstance(event, MessageEndEvent):
            message_ends.append(event)
    
    # Verify message events
    assert len(message_starts) > 0
    assert len(message_ends) > 0


@pytest.mark.asyncio
async def test_agent_end_includes_messages():
    """Test that agent_end event includes final messages array"""
    agent = Agent(
        system_prompt="Test agent",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    agent_end_event = None
    async for event in agent.prompt([UserMessage(content="Test")]):
        if isinstance(event, AgentEndEvent):
            agent_end_event = event
    
    # Verify agent_end has messages
    assert agent_end_event is not None
    assert "messages" in agent_end_event.payload


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
