"""
Integration tests for Agent v2 with Gateway.

Tests complete flow:
1. Gateway receives message
2. Routes to Agent v2
3. Agent emits events
4. Gateway broadcasts events via WebSocket
5. Steering/follow-up work correctly
"""
import asyncio
import pytest

from openclaw.agents import Agent, AgentSession
from openclaw.agents.events import AgentEvent, AgentEventType
from openclaw.agents.thinking import ThinkingLevel
from openclaw.agents.types import UserMessage


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gateway
async def test_gateway_agent_integration():
    """Test Agent v2 with Gateway routing"""
    # Create agent
    agent = Agent(
        system_prompt="You are a helpful assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    session = AgentSession(agent)
    
    # Simulate gateway routing message to agent
    events = []
    async for event in session.prompt([UserMessage(content="Hello from gateway")]):
        events.append(event)
    
    # Verify agent executed
    assert len(events) > 0
    
    # Verify expected event types
    event_types = [e.type for e in events]
    assert AgentEventType.AGENT_START in event_types
    assert AgentEventType.AGENT_END in event_types


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gateway
async def test_gateway_websocket_broadcast():
    """Test that agent events can be broadcast via WebSocket"""
    # Create agent
    agent = Agent(
        system_prompt="You are a helpful assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Simulate WebSocket connection
    ws_messages = []
    
    async def broadcast_to_ws(event: AgentEvent):
        """Simulate broadcasting event to WebSocket"""
        ws_messages.append({
            "type": event.type.value,
            "payload": event.payload,
            "timestamp": event.timestamp
        })
    
    # Execute agent and broadcast events
    async for event in agent.prompt([UserMessage(content="Test message")]):
        await broadcast_to_ws(event)
    
    # Verify events were broadcast
    assert len(ws_messages) > 0
    assert any(msg["type"] == "agent_start" for msg in ws_messages)
    assert any(msg["type"] == "agent_end" for msg in ws_messages)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gateway
async def test_gateway_steering_integration():
    """Test steering works through gateway"""
    # Create agent
    agent = Agent(
        system_prompt="You are a helpful assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    session = AgentSession(agent)
    
    # Start agent
    events = []
    async for event in session.prompt([UserMessage(content="Initial message")]):
        events.append(event)
        
        # Simulate gateway receiving steering message
        if len(events) == 3:
            session.steer("Steering message from gateway")
    
    # Verify execution completed
    assert len(events) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gateway
async def test_gateway_followup_integration():
    """Test follow-up works through gateway"""
    # Create agent
    agent = Agent(
        system_prompt="You are a helpful assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    session = AgentSession(agent)
    
    # First turn
    turn1_events = []
    async for event in session.prompt([UserMessage(content="First turn")]):
        turn1_events.append(event)
    
    # Gateway queues follow-up
    session.follow_up("Follow-up from gateway")
    
    # Continue agent
    turn2_events = []
    async for event in session.continue_agent():
        turn2_events.append(event)
    
    # Verify both turns
    assert len(turn1_events) > 0
    assert len(turn2_events) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gateway
async def test_gateway_channel_integration():
    """Test Agent v2 with channel (Telegram/Discord)"""
    # Create agent
    agent = Agent(
        system_prompt="You are a helpful assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Simulate channel message routing through gateway to agent
    channel_messages = [
        UserMessage(content="Message from Telegram"),
        UserMessage(content="Follow-up from Telegram"),
    ]
    
    for msg in channel_messages:
        events = []
        async for event in agent.prompt([msg]):
            events.append(event)
        
        # Verify agent processed channel message
        assert len(events) > 0


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.gateway
async def test_gateway_event_stream_completion():
    """Test that gateway event stream completes properly"""
    # Create agent
    agent = Agent(
        system_prompt="You are a helpful assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Track completion
    completed = False
    events = []
    
    async for event in agent.prompt([UserMessage(content="Test")]):
        events.append(event)
        
        if event.type == AgentEventType.AGENT_END:
            completed = True
    
    # Verify stream completed
    assert completed
    assert len(events) > 0


if __name__ == "__main__":
    # Run gateway integration tests
    pytest.main([__file__, "-v", "-m", "gateway"])
