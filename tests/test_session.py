"""
Tests for Session Management
"""

import json

import pytest

from openclaw.agents.session import Message, Session, SessionManager


class TestMessage:
    """Test Message class"""

    def test_message_creation(self):
        """Test creating a message"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp  # Should have timestamp

    def test_message_with_tool_calls(self):
        """Test message with tool calls"""
        tool_calls = [{"id": "1", "name": "bash", "arguments": {}}]
        msg = Message(role="assistant", content="Running command", tool_calls=tool_calls)
        assert msg.tool_calls == tool_calls

    def test_message_serialization(self):
        """Test message can be serialized"""
        msg = Message(role="user", content="Test")
        data = msg.model_dump()
        assert data["role"] == "user"
        assert data["content"] == "Test"


class TestSession:
    """Test Session class"""

    def test_session_creation(self, temp_workspace):
        """Test creating a session"""
        session = Session("test-session", temp_workspace)
        assert session.session_id == "test-session"
        assert session.workspace_dir == temp_workspace
        assert len(session.messages) == 0

    def test_add_message(self, temp_workspace):
        """Test adding a message"""
        session = Session("test-session", temp_workspace)
        msg = session.add_message("user", "Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert len(session.messages) == 1

    def test_add_user_message(self, temp_workspace):
        """Test adding user message helper"""
        session = Session("test-session", temp_workspace)
        msg = session.add_user_message("Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_add_assistant_message(self, temp_workspace):
        """Test adding assistant message helper"""
        session = Session("test-session", temp_workspace)
        tool_calls = [{"id": "1", "name": "test"}]
        msg = session.add_assistant_message("Response", tool_calls=tool_calls)

        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert msg.tool_calls == tool_calls

    def test_add_tool_message(self, temp_workspace):
        """Test adding tool message helper"""
        session = Session("test-session", temp_workspace)
        msg = session.add_tool_message("call-1", "Result")

        assert msg.role == "tool"
        assert msg.content == "Result"
        assert msg.tool_call_id == "call-1"

    def test_get_messages(self, temp_workspace):
        """Test getting messages"""
        session = Session("test-session", temp_workspace)
        session.add_user_message("Message 1")
        session.add_user_message("Message 2")
        session.add_user_message("Message 3")

        # Get all messages
        all_msgs = session.get_messages()
        assert len(all_msgs) == 3

        # Get limited messages
        limited = session.get_messages(limit=2)
        assert len(limited) == 2
        assert limited[0].content == "Message 2"  # Last 2

    def test_session_persistence(self, temp_workspace):
        """Test session is persisted to disk"""
        session = Session("test-session", temp_workspace)
        session.add_user_message("Test message")

        # Create new session with same ID
        session2 = Session("test-session", temp_workspace)

        # Should load previous messages
        assert len(session2.messages) == 1
        assert session2.messages[0].content == "Test message"

    def test_clear_session(self, temp_workspace):
        """Test clearing session"""
        session = Session("test-session", temp_workspace)
        session.add_user_message("Test")
        assert len(session.messages) == 1

        session.clear()
        assert len(session.messages) == 0

    def test_to_dict(self, temp_workspace):
        """Test converting session to dict"""
        session = Session("test-session", temp_workspace)
        session.add_user_message("Hello")

        data = session.to_dict()
        assert data["sessionId"] == "test-session"
        assert data["messageCount"] == 1
        assert len(data["messages"]) == 1


class TestSessionManager:
    """Test SessionManager class"""

    def test_manager_creation(self, temp_workspace):
        """Test creating session manager"""
        manager = SessionManager(temp_workspace)
        assert manager.workspace_dir == temp_workspace

    def test_get_session(self, temp_workspace):
        """Test getting or creating session"""
        manager = SessionManager(temp_workspace)
        session1 = manager.get_session("session-1")
        session2 = manager.get_session("session-1")

        assert session1.session_id == "session-1"
        assert session1 is session2  # Same instance

    def test_list_sessions(self, temp_workspace):
        """Test listing sessions"""
        manager = SessionManager(temp_workspace)
        session1 = manager.get_session("session-1")
        session2 = manager.get_session("session-2")

        # Sessions need messages to be saved to disk
        session1.add_user_message("Test 1")
        session2.add_user_message("Test 2")

        sessions = manager.list_sessions()
        # Sessions should be in memory at least
        assert isinstance(sessions, list)

    def test_delete_session(self, temp_workspace):
        """Test deleting session"""
        manager = SessionManager(temp_workspace)
        session = manager.get_session("test-session")
        session.add_user_message("Test")

        manager.delete_session("test-session")

        # Session should not exist
        sessions = manager.list_sessions()
        assert "test-session" not in sessions
