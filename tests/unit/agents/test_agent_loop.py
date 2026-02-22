"""Unit tests for agent loop"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openclaw.agents.agent_loop import (
    AgentLoop,
    AgentMessage,
    AgentOptions,
    AgentState,
    default_convert_to_llm,
    default_transform_context,
)
from openclaw.agents.events import EventEmitter
from openclaw.agents.providers.base import LLMMessage, LLMProvider, LLMResponse
from openclaw.agents.tools.base import AgentTool, ToolResult


class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses=None):
        super().__init__(model="mock/model")
        self.responses = responses or []
        self.call_count = 0

    async def stream(self, messages, tools=None, max_tokens=4096, **kwargs):
        """Mock streaming."""
        self.call_count += 1
        yield LLMResponse(type="text_delta", content="Hello ")
        yield LLMResponse(type="text_delta", content="world")
        yield LLMResponse(type="done", content="")

    def get_client(self):
        return None

    @property
    def provider_name(self) -> str:
        return "mock"


class MockTool(AgentTool):
    """Mock tool for testing."""

    def __init__(self, name="test_tool"):
        # LegacyAgentTool.__init__ takes no arguments; set attributes directly
        super().__init__()
        self.name = name
        self.description = "Test tool"
        self.execute_count = 0

    async def execute(self, params):
        self.execute_count += 1
        return ToolResult(success=True, content=f"Tool executed with {params}")


@pytest.fixture
def mock_provider():
    """Create mock provider"""
    return MockProvider()


@pytest.fixture
def mock_tool():
    """Create mock tool"""
    return MockTool()


@pytest.fixture
def event_emitter():
    """Create event emitter"""
    return EventEmitter()


@pytest.fixture
def agent_loop(mock_provider, mock_tool, event_emitter):
    """Create agent loop"""
    return AgentLoop(
        provider=mock_provider,
        tools=[mock_tool],
        event_emitter=event_emitter
    )


class TestAgentMessage:
    """Test AgentMessage class"""
    
    def test_create_message(self):
        """Test creating agent message"""
        msg = AgentMessage(role="user", content="test")
        assert msg.role == "user"
        assert msg.content == "test"
        assert msg.custom is False
    
    def test_custom_message(self):
        """Test custom message flag"""
        msg = AgentMessage(role="custom", content="test", custom=True)
        assert msg.custom is True


class TestAgentOptions:
    """Test AgentOptions class"""
    
    def test_default_options(self):
        """Test default options"""
        opts = AgentOptions()
        assert opts.steering_mode == "one-at-a-time"
        assert opts.follow_up_mode == "one-at-a-time"
        assert opts.stream_fn is None
        assert opts.session_id is None
    
    def test_custom_options(self):
        """Test custom options"""
        opts = AgentOptions(
            steering_mode="all",
            follow_up_mode="all",
            session_id="test-session"
        )
        assert opts.steering_mode == "all"
        assert opts.follow_up_mode == "all"
        assert opts.session_id == "test-session"


class TestConvertToLlm:
    """Test message conversion"""
    
    def test_convert_basic_messages(self):
        """Test converting basic messages"""
        messages = [
            AgentMessage(role="user", content="Hello"),
            AgentMessage(role="assistant", content="Hi"),
        ]
        
        llm_messages = default_convert_to_llm(messages)
        
        assert len(llm_messages) == 2
        assert llm_messages[0].role == "user"
        assert llm_messages[0].content == "Hello"
        assert llm_messages[1].role == "assistant"
        assert llm_messages[1].content == "Hi"
    
    def test_filter_custom_messages(self):
        """Test filtering custom messages"""
        messages = [
            AgentMessage(role="user", content="Hello"),
            AgentMessage(role="custom", content="Internal", custom=True),
            AgentMessage(role="assistant", content="Hi"),
        ]
        
        llm_messages = default_convert_to_llm(messages)
        
        assert len(llm_messages) == 2
        assert all(not msg.content == "Internal" for msg in llm_messages)
    
    def test_preserve_tool_calls(self):
        """Test preserving tool calls"""
        messages = [
            AgentMessage(
                role="assistant",
                content="",
                tool_calls=[{"name": "test", "params": {}}]
            ),
        ]
        
        llm_messages = default_convert_to_llm(messages)
        
        assert len(llm_messages) == 1
        assert llm_messages[0].tool_calls is not None


class TestTransformContext:
    """Test context transformation"""
    
    def test_default_transform(self):
        """Test default transform (no-op)"""
        messages = [
            LLMMessage(role="user", content="Test"),
        ]
        
        transformed = default_transform_context(messages)
        
        assert len(transformed) == len(messages)
        assert transformed[0].content == "Test"


class TestAgentState:
    """Test agent state"""
    
    def test_initial_state(self):
        """Test initial state"""
        state = AgentState()
        
        assert len(state.messages) == 0
        assert state.turn_number == 0
        assert state.is_streaming is False
        assert state.stream_message is None
        assert len(state.pending_tool_calls) == 0
    
    def test_abort_signal(self):
        """Test abort signal"""
        state = AgentState()
        
        assert state.signal is not None
        assert not state.signal.aborted


@pytest.mark.asyncio
class TestAgentLoop:
    """Test agent loop"""
    
    async def test_create_loop(self, agent_loop):
        """Test creating agent loop"""
        assert agent_loop is not None
        assert agent_loop.provider is not None
        assert len(agent_loop.tools) > 0
    
    async def test_stream_response(self, agent_loop):
        """Test streaming response"""
        agent_loop.state.messages = [
            AgentMessage(role="user", content="Hello")
        ]
        
        message, tool_calls = await agent_loop.stream_assistant_response()
        
        assert message.role == "assistant"
        assert "Hello" in message.content or "world" in message.content
        assert isinstance(tool_calls, list)
    
    async def test_steer(self, agent_loop):
        """Test steering"""
        agent_loop.steer("Stop now")
        
        assert len(agent_loop.state.steering_queue) == 1
        assert agent_loop.state.steering_queue[0] == "Stop now"
    
    async def test_followup(self, agent_loop):
        """Test follow-up"""
        agent_loop.followup("Continue with this")
        
        assert len(agent_loop.state.followup_queue) == 1
        assert agent_loop.state.followup_queue[0] == "Continue with this"
    
    async def test_abort(self, agent_loop):
        """Test abort"""
        agent_loop.abort()
        
        assert agent_loop.state.signal.aborted


@pytest.mark.asyncio
class TestEventEmission:
    """Test event emission"""
    
    async def test_emits_agent_start(self, agent_loop):
        """Test agent start event"""
        events = []
        
        def handler(event):
            events.append(event)
        
        agent_loop.event_emitter.on("agent_start", handler)
        
        # Start agent loop (will emit event)
        task = asyncio.create_task(
            agent_loop.agent_loop(["test"], model="test-model")
        )
        
        # Wait a bit for event
        await asyncio.sleep(0.1)
        
        # Cancel task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        assert len(events) > 0
        assert events[0].type == "agent_start"


@pytest.mark.asyncio
class TestToolExecution:
    """Test tool execution"""
    
    async def test_execute_tool(self, agent_loop, mock_tool):
        """Test executing tool"""
        tool_calls = [{
            "id": "call_1",
            "name": "test_tool",
            "params": {"test": "value"}
        }]
        
        await agent_loop.execute_tool_calls(tool_calls)
        
        assert mock_tool.execute_count == 1
        assert len(agent_loop.state.messages) > 0
        
        # Check tool result was added
        result_msg = agent_loop.state.messages[-1]
        assert result_msg.role == "toolResult"
        assert result_msg.tool_call_id == "call_1"
    
    async def test_execute_nonexistent_tool(self, agent_loop):
        """Test executing nonexistent tool"""
        tool_calls = [{
            "id": "call_1",
            "name": "nonexistent",
            "params": {}
        }]
        
        await agent_loop.execute_tool_calls(tool_calls)
        
        # Should add error message
        assert len(agent_loop.state.messages) > 0
        result_msg = agent_loop.state.messages[-1]
        assert "not found" in result_msg.content.lower()


def test_agent_options_modes():
    """Test agent options modes"""
    # One at a time mode
    opts1 = AgentOptions(
        steering_mode="one-at-a-time",
        follow_up_mode="one-at-a-time"
    )
    assert opts1.steering_mode == "one-at-a-time"
    assert opts1.follow_up_mode == "one-at-a-time"
    
    # All mode
    opts2 = AgentOptions(
        steering_mode="all",
        follow_up_mode="all"
    )
    assert opts2.steering_mode == "all"
    assert opts2.follow_up_mode == "all"
