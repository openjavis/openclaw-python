"""
Tests for Agent Runtime
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from openclaw.agents.runtime import AgentEvent, AgentRuntime
from openclaw.agents.session import Session


class TestAgentRuntime:
    """Test AgentRuntime class"""

    def test_init_default(self):
        """Test runtime initialization with defaults"""
        runtime = AgentRuntime()
        assert runtime.model_str == "anthropic/claude-opus-4-5-20250514"
        assert runtime.api_key is None

    def test_init_custom(self):
        """Test runtime initialization with custom values"""
        runtime = AgentRuntime(model="openai/gpt-4o", api_key="test-key")
        assert runtime.model_str == "openai/gpt-4o"
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
        # Skip - new runtime formats tools internally during run_turn
        pytest.skip("New runtime uses provider-based tool formatting")

    @pytest.mark.asyncio
    async def test_run_turn_adds_user_message(self, temp_workspace):
        """Test that run_turn adds user message to session"""
        runtime = AgentRuntime()
        session = Session("test-session", temp_workspace)

        # Mock the provider's stream method to avoid actual API call
        with patch.object(runtime.provider, "stream", new_callable=AsyncMock) as mock_stream:
            # Make the mock return an empty async generator
            async def mock_generator():
                yield type("obj", (object,), {"type": "done", "content": None})()

            mock_stream.return_value = mock_generator()

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
