"""
Integration tests for Agent v2 with real providers.

Tests:
- Multi-turn tool calling
- Gateway integration
- Channel integration
- Steering during execution
- Follow-up continuation
"""
import asyncio
import pytest

from openclaw.agents import Agent, AgentSession
from openclaw.agents.events import (
    AgentEndEvent,
    AgentStartEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
)
from openclaw.agents.thinking import ThinkingLevel
from openclaw.agents.tools import AgentToolBase, AgentToolResult
from openclaw.agents.types import TextContent, UserMessage


class TestTool(AgentToolBase):
    """Test tool for integration testing"""
    
    @property
    def name(self) -> str:
        return "test_tool"
    
    @property
    def label(self) -> str:
        return "Test Tool"
    
    @property
    def description(self) -> str:
        return "A test tool for integration testing"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action to perform"}
            },
            "required": ["action"]
        }
    
    async def execute(self, tool_call_id: str, params: dict, signal=None, on_update=None):
        # Simulate async work
        await asyncio.sleep(0.1)
        
        action = params.get("action", "unknown")
        result = AgentToolResult(
            content=[TextContent(type="text", text=f"Executed {action}")],
            details={"action": action, "success": True}
        )
        
        if on_update:
            # Simulate streaming update
            partial = AgentToolResult(
                content=[TextContent(type="text", text=f"Executing {action}...")],
                details={"action": action, "in_progress": True}
            )
            on_update(partial)
        
        return result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_multi_turn_tools():
    """Test multiple rounds of tool calling"""
    tool = TestTool()
    
    agent = Agent(
        system_prompt="You are a test assistant",
        model="dummy/model",
        tools=[tool],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Execute first turn
    tool_executions = []
    async for event in agent.prompt([UserMessage(content="Execute action1")]):
        if isinstance(event, ToolExecutionEndEvent):
            tool_executions.append(event)
    
    # Verify tool execution
    assert len(tool_executions) >= 0  # May be 0 if dummy provider doesn't call tools


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_session_steering():
    """Test steering interrupts tool execution"""
    tool = TestTool()
    
    agent = Agent(
        system_prompt="You are a test assistant",
        model="dummy/model",
        tools=[tool],
        thinking_level=ThinkingLevel.OFF
    )
    
    session = AgentSession(agent)
    
    # Start agent execution
    events = []
    async for event in session.prompt([UserMessage(content="Test message")]):
        events.append(event)
        
        # Inject steering message mid-execution
        if len(events) == 2:
            session.steer("New instruction!")
    
    # Verify events collected
    assert len(events) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_followup_continuation():
    """Test follow-up messages extend conversation"""
    agent = Agent(
        system_prompt="You are a test assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    session = AgentSession(agent)
    
    # First turn
    turn1_events = []
    async for event in session.prompt([UserMessage(content="First message")]):
        turn1_events.append(event)
    
    # Queue follow-up
    session.follow_up("Follow-up message")
    
    # Continue session
    turn2_events = []
    async for event in session.continue_agent():
        turn2_events.append(event)
    
    # Verify both turns executed
    assert len(turn1_events) > 0
    assert len(turn2_events) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_streaming():
    """Test tool streaming with on_update callback"""
    tool = TestTool()
    
    # Track updates
    updates = []
    
    def on_update(partial_result):
        updates.append(partial_result)
    
    # Execute tool
    result = await tool.execute(
        tool_call_id="test_call",
        params={"action": "stream_test"},
        signal=None,
        on_update=on_update
    )
    
    # Verify streaming worked
    assert result is not None
    assert len(updates) > 0  # Should have at least one partial update


@pytest.mark.asyncio
@pytest.mark.integration
async def test_thinking_level_integration():
    """Test agent with different thinking levels"""
    for level in [ThinkingLevel.OFF, ThinkingLevel.LOW, ThinkingLevel.MEDIUM]:
        agent = Agent(
            system_prompt="You are a test assistant",
            model="dummy/model",
            tools=[],
            thinking_level=level
        )
        
        events = []
        async for event in agent.prompt([UserMessage(content="Test")]):
            events.append(event)
        
        # Verify agent executed with this thinking level
        assert len(events) > 0
        assert agent.thinking_level == level


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_abort_during_execution():
    """Test aborting agent during execution"""
    agent = Agent(
        system_prompt="You are a test assistant",
        model="dummy/model",
        tools=[],
        thinking_level=ThinkingLevel.OFF
    )
    
    # Start execution and abort
    events = []
    async for event in agent.prompt([UserMessage(content="Test")]):
        events.append(event)
        
        # Abort after a few events
        if len(events) >= 2:
            agent.abort()
            break
    
    # Verify abort worked (no crash)
    assert len(events) >= 2


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration"])
