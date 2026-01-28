"""
Tests for Agent Runtime
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from clawdbot.agents.runtime import AgentEvent, AgentRuntime
from clawdbot.agents.session import Session


class TestAgentRuntime:
    """Test AgentRuntime class"""

    def test_init_default(self):
        """Test runtime initialization with defaults"""
        runtime = AgentRuntime()
        assert runtime.model == "anthropic/claude-opus-4-5-20250514"
        assert runtime.api_key is None

    def test_init_custom(self):
        """Test runtime initialization with custom values"""
        runtime = AgentRuntime(model="openai/gpt-4o", api_key="test-key")
        assert runtime.model == "openai/gpt-4o"
        assert runtime.api_key == "test-key"

    def test_get_client_anthropic(self, mock_api_key):
        """Test getting Anthropic client"""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": mock_api_key}):
            AgentRuntime(model="anthropic/claude-opus-4")
            # Skip - runtime refactored to use provider pattern
            pytest.skip("Runtime refactored to use provider pattern")

    def test_get_client_openai(self, mock_api_key):
        """Test getting OpenAI client"""
        # Skip - runtime refactored to use provider pattern
        pytest.skip("Runtime refactored to use provider pattern")

    def test_format_tools_for_api(self):
        """Test tool formatting for API"""
        runtime = AgentRuntime()

        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.get_schema.return_value = {"type": "object"}

        formatted = runtime._format_tools_for_api([mock_tool])

        assert len(formatted) == 1
        assert formatted[0]["name"] == "test_tool"
        assert formatted[0]["description"] == "A test tool"
        assert formatted[0]["input_schema"] == {"type": "object"}

    @pytest.mark.asyncio
    async def test_run_turn_adds_user_message(self, temp_workspace):
        """Test that run_turn adds user message to session"""
        runtime = AgentRuntime()
        session = Session("test-session", temp_workspace)

        # Mock the client to avoid actual API call
        with patch.object(runtime, "_get_client"):
            with patch.object(runtime, "_run_anthropic", new_callable=AsyncMock):
                async for _ in runtime.run_turn(session, "Hello"):
                    break

        assert len(session.messages) >= 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"


class TestAgentEvent:
    """Test AgentEvent class"""

    def test_event_creation(self):
        """Test creating an event"""
        event = AgentEvent("test", {"key": "value"})
        assert event.type == "test"
        assert event.data == {"key": "value"}

    def test_event_types(self):
        """Test different event types"""
        lifecycle = AgentEvent("lifecycle", {"phase": "start"})
        assert lifecycle.type == "lifecycle"

        assistant = AgentEvent("assistant", {"delta": {"text": "Hi"}})
        assert assistant.type == "assistant"

        tool = AgentEvent("tool", {"toolName": "bash"})
        assert tool.type == "tool"
