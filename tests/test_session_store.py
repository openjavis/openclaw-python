"""
Tests for SessionStore
"""
import tempfile
from pathlib import Path

import pytest

from openclaw.agents.session_store import (
    SessionEntry,
    SessionResetConfig,
    SessionStore,
    TranscriptMessage,
)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_store(temp_workspace):
    """Create SessionStore instance"""
    return SessionStore(temp_workspace)


def test_create_session(session_store):
    """Test creating a new session"""
    entry, is_new = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345",
        model="google/gemini-3-pro-preview",
    )
    
    assert is_new is True
    assert entry.session_key == "agent:main:telegram:user:12345"
    assert entry.model == "google/gemini-3-pro-preview"
    assert entry.message_count == 0


def test_get_existing_session(session_store):
    """Test retrieving existing session"""
    # Create session
    entry1, _ = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Get same session
    entry2, is_new = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    assert is_new is False
    assert entry1.session_id == entry2.session_id


def test_save_and_load_transcript(session_store):
    """Test saving and loading transcript"""
    entry, _ = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Create messages
    messages = [
        TranscriptMessage(role="user", content="Hello"),
        TranscriptMessage(role="assistant", content="Hi there!"),
        TranscriptMessage(role="user", content="How are you?"),
    ]
    
    # Save transcript
    session_store.save_transcript(entry.session_id, messages)
    
    # Load transcript
    loaded = session_store.load_transcript(entry.session_id)
    
    assert len(loaded) == 3
    assert loaded[0].role == "user"
    assert loaded[0].content == "Hello"
    assert loaded[1].role == "assistant"
    assert loaded[1].content == "Hi there!"


def test_append_message(session_store):
    """Test appending messages to transcript"""
    entry, _ = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Append messages one by one
    session_store.append_message(
        entry.session_id,
        TranscriptMessage(role="user", content="Message 1")
    )
    session_store.append_message(
        entry.session_id,
        TranscriptMessage(role="assistant", content="Response 1")
    )
    
    # Load transcript
    loaded = session_store.load_transcript(entry.session_id)
    
    assert len(loaded) == 2
    assert loaded[0].content == "Message 1"
    assert loaded[1].content == "Response 1"


def test_session_reset(session_store):
    """Test session reset"""
    entry, _ = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Add some messages
    for i in range(5):
        session_store.append_message(
            entry.session_id,
            TranscriptMessage(role="user", content=f"Message {i}")
        )
    
    # Update token count
    session_store.update_session(
        entry.session_id,
        token_count={"input": 1000, "output": 500}
    )
    
    # Reset session
    result = session_store.reset_session(entry.session_id, "test_reset")
    
    assert result is True
    
    # Check transcript is cleared
    loaded = session_store.load_transcript(entry.session_id)
    assert len(loaded) == 0
    
    # Check counters are reset
    entry = session_store.get_session(entry.session_id)
    assert entry.message_count == 0
    assert entry.token_count["input"] == 0
    assert entry.token_count["output"] == 0
    assert entry.last_reset_at is not None


def test_session_reset_triggers(temp_workspace):
    """Test session reset triggers"""
    reset_config = SessionResetConfig(
        daily_reset_hour=None,  # Disable daily reset
        idle_minutes=None,
        max_tokens=1000,
        max_messages=10,
    )
    
    store = SessionStore(temp_workspace, reset_config=reset_config)
    
    entry, _ = store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Should not reset yet
    should_reset, reason = store.should_reset(entry.session_id)
    assert should_reset is False
    
    # Exceed token limit
    store.update_session(
        entry.session_id,
        token_count={"input": 800, "output": 300}  # Total: 1100 > 1000
    )
    
    should_reset, reason = store.should_reset(entry.session_id)
    assert should_reset is True
    assert reason == "token_limit"


def test_list_sessions(session_store):
    """Test listing sessions"""
    # Create multiple sessions
    session_store.get_or_create_session(
        session_key="agent:main:telegram:user:1"
    )
    session_store.get_or_create_session(
        session_key="agent:main:telegram:user:2"
    )
    session_store.get_or_create_session(
        session_key="agent:main:discord:user:3"
    )
    
    # List all sessions
    all_sessions = session_store.list_sessions()
    assert len(all_sessions) == 3
    
    # List filtered sessions
    telegram_sessions = session_store.list_sessions(
        session_key_prefix="agent:main:telegram"
    )
    assert len(telegram_sessions) == 2


def test_delete_session(session_store):
    """Test deleting session"""
    entry, _ = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Add some messages
    session_store.append_message(
        entry.session_id,
        TranscriptMessage(role="user", content="Test")
    )
    
    # Delete session
    result = session_store.delete_session(entry.session_id)
    assert result is True
    
    # Verify deleted
    assert session_store.get_session(entry.session_id) is None
    loaded = session_store.load_transcript(entry.session_id)
    assert len(loaded) == 0


def test_tool_calls_in_transcript(session_store):
    """Test that tool_calls are correctly saved in transcript"""
    entry, _ = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Create message with tool_calls
    message = TranscriptMessage(
        role="assistant",
        content="Let me search for that",
        tool_calls=[{
            "id": "call_123",
            "name": "web_search",
            "arguments": {"query": "python tutorial"}
        }]
    )
    
    session_store.append_message(entry.session_id, message)
    
    # Load and verify
    loaded = session_store.load_transcript(entry.session_id)
    assert len(loaded) == 1
    assert loaded[0].tool_calls is not None
    assert len(loaded[0].tool_calls) == 1
    assert loaded[0].tool_calls[0]["name"] == "web_search"


def test_tool_result_message(session_store):
    """Test that tool result messages are correctly saved"""
    entry, _ = session_store.get_or_create_session(
        session_key="agent:main:telegram:user:12345"
    )
    
    # Create tool result message
    message = TranscriptMessage(
        role="tool",
        content="Search results: ...",
        tool_call_id="call_123",
        name="web_search"
    )
    
    session_store.append_message(entry.session_id, message)
    
    # Load and verify
    loaded = session_store.load_transcript(entry.session_id)
    assert len(loaded) == 1
    assert loaded[0].role == "tool"
    assert loaded[0].tool_call_id == "call_123"
    assert loaded[0].name == "web_search"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
