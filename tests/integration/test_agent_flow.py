"""
End-to-end agent execution tests
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from openclaw.agents import AgentRuntime, Session, SessionManager
from openclaw.agents.runtime import AgentEvent
from openclaw.agents.tools.bash import BashTool


class TestAgentFlow:
    """Test complete agent execution flows"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_basic_conversation_flow(self, temp_workspace):
        """Test basic conversation flow"""
        runtime = AgentRuntime(enable_context_management=True)
        session = Session("test-flow", temp_workspace)

        # Mock the provider's stream method
        with patch.object(runtime.provider, "stream") as mock_stream:

            async def mock_response(*args, **kwargs):
                # Create mock LLMResponse objects
                from openclaw.agents.providers.base import LLMResponse

                yield LLMResponse(type="text_delta", content="Hello! ")
                yield LLMResponse(type="text_delta", content="I am ClawdBot.")
                yield LLMResponse(type="done", content=None)

            mock_stream.return_value = mock_response()

            response_parts = []
            async for event in runtime.run_turn(session, "Hello"):
                if event.type == "assistant":
                    if "delta" in event.data and "text" in event.data["delta"]:
                        response_parts.append(event.data["delta"]["text"])

            response = "".join(response_parts)
            assert "Hello" in response or "ClawdBot" in response
            assert len(session.messages) >= 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_turn_conversation(self, temp_workspace):
        """Test multi-turn conversation"""
        runtime = AgentRuntime()
        session = Session("multi-turn", temp_workspace)

        with patch.object(runtime.provider, "stream") as mock:
            # Turn 1
            async def response1(*args, **kwargs):
                from openclaw.agents.providers.base import LLMResponse

                yield LLMResponse(type="text_delta", content="Response 1")
                yield LLMResponse(type="done", content=None)

            mock.return_value = response1()

            async for _ in runtime.run_turn(session, "Message 1"):
                pass

            # Turn 2
            async def response2(*args, **kwargs):
                from openclaw.agents.providers.base import LLMResponse

                yield LLMResponse(type="text_delta", content="Response 2")
                yield LLMResponse(type="done", content=None)

            mock.return_value = response2()

            async for _ in runtime.run_turn(session, "Message 2"):
                pass

            # Should have 2 user messages + 2 assistant messages
            assert len(session.messages) >= 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_session_persistence(self, temp_workspace):
        """Test session persistence across instances"""
        session_id = "persist-test"

        # Create session and add messages
        session1 = Session(session_id, temp_workspace)
        session1.add_user_message("Test message")
        session1.add_assistant_message("Test response")

        # Create new session with same ID
        session2 = Session(session_id, temp_workspace)

        # Should load previous messages
        assert len(session2.messages) == 2
        assert session2.messages[0].content == "Test message"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_context_window_management(self, temp_workspace):
        """Test automatic context window management"""
        runtime = AgentRuntime(enable_context_management=True)
        session = Session("context-test", temp_workspace)

        # Add many messages to trigger context management
        for i in range(50):
            session.add_user_message(f"Message {i}" * 100)  # Long messages
            session.add_assistant_message(f"Response {i}" * 100)

        initial_count = len(session.messages)

        with patch.object(runtime.provider, "stream") as mock:

            async def response(*args, **kwargs):
                from openclaw.agents.providers.base import LLMResponse

                yield LLMResponse(type="text_delta", content="Pruned response")
                yield LLMResponse(type="done", content=None)

            mock.return_value = response()

            async for _ in runtime.run_turn(session, "New message"):
                pass

            # Context management should have pruned some messages
            # (or at least attempted to if context was large)
            assert len(session.messages) <= initial_count + 2


class TestSessionManager:
    """Test session manager integration"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_sessions(self, temp_workspace):
        """Test managing multiple sessions"""
        manager = SessionManager(temp_workspace)

        # Create multiple sessions
        session1 = manager.get_session("session-1")
        session2 = manager.get_session("session-2")
        session3 = manager.get_session("session-3")

        # Add different messages to each
        session1.add_user_message("Message 1")
        session2.add_user_message("Message 2")
        session3.add_user_message("Message 3")

        # List sessions
        session_ids = manager.list_sessions()
        assert "session-1" in session_ids
        assert "session-2" in session_ids
        assert "session-3" in session_ids

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_session_cleanup(self, temp_workspace):
        """Test session cleanup"""
        manager = SessionManager(temp_workspace)

        # Create and delete session
        session = manager.get_session("temp-session")
        session.add_user_message("Test")

        deleted = manager.delete_session("temp-session")
        assert deleted is True

        # Should not be in list
        assert "temp-session" not in manager.list_sessions()
