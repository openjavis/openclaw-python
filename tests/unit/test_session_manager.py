"""Unit tests for session manager"""

import pytest
import tempfile
from pathlib import Path

from openclaw.agents.session import SessionManager, Session


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_session_manager_initialization(temp_workspace):
    """Test session manager initialization"""
    manager = SessionManager(workspace_dir=temp_workspace)
    assert manager is not None
    assert len(manager.list_sessions()) == 0


def test_create_session(temp_workspace):
    """Test session creation"""
    manager = SessionManager(workspace_dir=temp_workspace)
    session = manager.get_session("test-session")
    
    assert isinstance(session, Session)
    assert session.session_id == "test-session"


def test_get_existing_session(temp_workspace):
    """Test retrieving existing session"""
    manager = SessionManager(workspace_dir=temp_workspace)
    
    session1 = manager.get_session("test-session")
    session2 = manager.get_session("test-session")
    
    assert session1 is session2


def test_list_sessions(temp_workspace):
    """Test listing all sessions"""
    manager = SessionManager(workspace_dir=temp_workspace)
    
    manager.get_session("session-1")
    manager.get_session("session-2")
    manager.get_session("session-3")
    
    sessions = manager.list_sessions()
    assert len(sessions) == 3
    assert "session-1" in sessions
    assert "session-2" in sessions
    assert "session-3" in sessions


def test_session_messages(temp_workspace):
    """Test adding and retrieving messages"""
    manager = SessionManager(workspace_dir=temp_workspace)
    session = manager.get_session("test-session")
    
    session.add_user_message("Hello")
    session.add_assistant_message("Hi there!")
    
    messages = session.get_messages()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there!"


def test_session_clear(temp_workspace):
    """Test clearing session messages"""
    manager = SessionManager(workspace_dir=temp_workspace)
    session = manager.get_session("test-session")
    
    session.add_user_message("Message 1")
    session.add_user_message("Message 2")
    assert len(session.get_messages()) == 2
    
    session.clear()
    assert len(session.get_messages()) == 0
