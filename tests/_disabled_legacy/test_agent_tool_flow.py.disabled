"""Integration tests for agent tool execution flow"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from openclaw.agents import Agent
from openclaw.agents.providers.base import LLMProvider, LLMResponse
from openclaw.agents.tools.base import AgentTool, ToolResult


class MockProvider(LLMProvider):
    """Mock provider that returns tool calls"""
    
    def __init__(self, tool_name: str = "test_tool"):
        super().__init__()
        self.tool_name = tool_name
        self.call_count = 0
    
    async def stream(self, messages, model, tools=None):
        """Mock streaming with tool call"""
        self.call_count += 1
        
        if self.call_count == 1:
            # First call: return tool call
            yield LLMResponse(type="text_delta", content="Let me use the tool.")
            yield LLMResponse(
                type="tool_call",
                tool_calls=[{
                    "id": "call_1",
                    "name": self.tool_name,
                    "arguments": {"param": "value"}
                }]
            )
            yield LLMResponse(type="done", content="")
        else:
            # Second call: return final response
            yield LLMResponse(type="text_delta", content="Tool result received. Done!")
            yield LLMResponse(type="done", content="")


class CounterTool(AgentTool):
    """Tool that counts executions"""
    
    def __init__(self):
        super().__init__(
            name="counter",
            description="A counter tool",
            parameters={
                "type": "object",
                "properties": {
                    "action": {"type": "string"}
                }
            }
        )
        self.execution_count = 0
    
    async def execute(self, params):
        self.execution_count += 1
        return ToolResult(
            success=True,
            content=f"Executed {self.execution_count} times"
        )


@pytest.mark.asyncio
class TestAgentToolFlow:
    """Test agent tool execution flow"""
    
    async def test_single_tool_execution(self):
        """Test executing single tool"""
        provider = MockProvider(tool_name="counter")
        counter_tool = CounterTool()
        
        agent = Agent(
            provider=provider,
            tools=[counter_tool]
        )
        
        messages = await agent.prompt("Use the counter tool")
        
        # Tool should have been executed
        assert counter_tool.execution_count == 1
        
        # Should have messages including tool result
        assert len(messages) > 0
    
    async def test_tool_result_in_messages(self):
        """Test that tool results appear in messages"""
        provider = MockProvider(tool_name="counter")
        counter_tool = CounterTool()
        
        agent = Agent(
            provider=provider,
            tools=[counter_tool]
        )
        
        messages = await agent.prompt("Use the counter tool")
        
        # Find tool result message
        tool_results = [
            msg for msg in messages
            if hasattr(msg, 'role') and msg.role == "toolResult"
        ]
        
        assert len(tool_results) > 0
    
    async def test_multiple_turns_with_tools(self):
        """Test multiple turns with tool execution"""
        provider = MockProvider(tool_name="counter")
        counter_tool = CounterTool()
        
        agent = Agent(
            provider=provider,
            tools=[counter_tool]
        )
        
        # First turn
        await agent.prompt("Use the counter")
        assert counter_tool.execution_count == 1
        
        # Reset provider for second turn
        provider.call_count = 0
        
        # Second turn (continue conversation)
        await agent.prompt("Use it again")
        
        # Counter should have been called twice total
        assert counter_tool.execution_count == 2


@pytest.mark.asyncio
class TestToolExecutionEvents:
    """Test tool execution events"""
    
    async def test_tool_execution_start_event(self):
        """Test tool execution start event"""
        provider = MockProvider(tool_name="counter")
        counter_tool = CounterTool()
        
        agent = Agent(
            provider=provider,
            tools=[counter_tool]
        )
        
        events_received = []
        
        def event_handler(event):
            events_received.append(event.type)
        
        agent.on("tool_execution_start", event_handler)
        
        await agent.prompt("Use the counter")
        
        # Should have received tool execution start event
        assert "tool_execution_start" in events_received
    
    async def test_tool_execution_end_event(self):
        """Test tool execution end event"""
        provider = MockProvider(tool_name="counter")
        counter_tool = CounterTool()
        
        agent = Agent(
            provider=provider,
            tools=[counter_tool]
        )
        
        events_received = []
        
        def event_handler(event):
            events_received.append(event.type)
        
        agent.on("tool_execution_end", event_handler)
        
        await agent.prompt("Use the counter")
        
        # Should have received tool execution end event
        assert "tool_execution_end" in events_received


@pytest.mark.asyncio
class TestToolErrors:
    """Test tool error handling"""
    
    async def test_tool_execution_error(self):
        """Test handling of tool execution errors"""
        
        class FailingTool(AgentTool):
            def __init__(self):
                super().__init__(
                    name="failing",
                    description="A failing tool",
                    parameters={"type": "object", "properties": {}}
                )
            
            async def execute(self, params):
                raise Exception("Tool failed")
        
        provider = MockProvider(tool_name="failing")
        failing_tool = FailingTool()
        
        agent = Agent(
            provider=provider,
            tools=[failing_tool]
        )
        
        messages = await agent.prompt("Use the failing tool")
        
        # Should handle error gracefully
        assert len(messages) > 0
        
        # Should have error in tool result
        tool_results = [
            msg for msg in messages
            if hasattr(msg, 'role') and msg.role == "toolResult"
        ]
        
        if tool_results:
            assert "error" in str(tool_results[0].content).lower() or "fail" in str(tool_results[0].content).lower()
    
    async def test_nonexistent_tool(self):
        """Test calling nonexistent tool"""
        provider = MockProvider(tool_name="nonexistent")
        
        agent = Agent(
            provider=provider,
            tools=[]  # No tools
        )
        
        messages = await agent.prompt("Use nonexistent tool")
        
        # Should handle gracefully
        assert len(messages) > 0
