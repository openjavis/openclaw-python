"""
Tests for session utilities
"""

import pytest
import tempfile
from pathlib import Path
from openclaw.agents.session_entry import SessionEntry
from openclaw.config.sessions.store import save_session_store
from openclaw.gateway.session_utils import (
    resolve_session_store_key,
    resolve_main_session_key,
    classify_session_key,
    derive_session_title,
    SessionsListOptions,
    list_sessions_from_store,
)


def test_resolve_session_store_key():
    """Test session key resolution"""
    # Special keys
    assert resolve_session_store_key("global") == "global"
    assert resolve_session_store_key("unknown") == "unknown"
    
    # Agent keys
    assert resolve_session_store_key("agent:main:main") == "agent:main:main"
    assert resolve_session_store_key("agent:main:dm:user123") == "agent:main:dm:user123"


def test_resolve_main_session_key():
    """Test main session key resolution"""
    key = resolve_main_session_key("main")
    assert key == "agent:main:main"
    
    key = resolve_main_session_key("test-agent")
    assert key == "agent:test-agent:main"


def test_classify_session_key():
    """Test session key classification"""
    assert classify_session_key("global") == "global"
    assert classify_session_key("unknown") == "unknown"
    assert classify_session_key("agent:main:main") == "direct"
    assert classify_session_key("agent:main:dm:user123") == "direct"
    assert classify_session_key("agent:main:group:456") == "group"
    assert classify_session_key("agent:main:channel:789") == "group"


def test_classify_session_with_entry():
    """Test classification with entry context"""
    # Direct chat
    entry_dm = SessionEntry(
        session_id="dm-123",
        updated_at=1000000,
        chat_type="dm"
    )
    assert classify_session_key("agent:main:test", entry_dm) == "direct"
    
    # Group chat
    entry_group = SessionEntry(
        session_id="group-123",
        updated_at=1000000,
        chat_type="group",
        group_id="group456"
    )
    assert classify_session_key("agent:main:test", entry_group) == "group"


def test_derive_session_title():
    """Test session title derivation"""
    # 1. Display name
    entry1 = SessionEntry(
        session_id="title-test-1",
        updated_at=1000000,
        display_name="My Display Name",
        subject="Subject Text"
    )
    assert derive_session_title(entry1) == "My Display Name"
    
    # 2. Subject
    entry2 = SessionEntry(
        session_id="title-test-2",
        updated_at=1000000,
        subject="Subject Text"
    )
    assert derive_session_title(entry2) == "Subject Text"
    
    # 3. First user message
    entry3 = SessionEntry(
        session_id="title-test-3",
        updated_at=1000000
    )
    assert derive_session_title(entry3, "Hello, how are you?") == "Hello, how are you?"
    
    # 4. Session ID prefix
    entry4 = SessionEntry(
        session_id="12345678-abcd-efgh",
        updated_at=1000000
    )
    assert derive_session_title(entry4) == "12345678"


def test_list_sessions_from_store():
    """Test listing sessions with filtering"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "sessions.json"
        
        # Create test store
        store = {
            "agent:main:session1": SessionEntry(
                session_id="s1",
                updated_at=3000000,
                label="Label A",
                thinking_level="high"
            ),
            "agent:main:session2": SessionEntry(
                session_id="s2",
                updated_at=2000000,
                label="Label B"
            ),
            "agent:main:session3": SessionEntry(
                session_id="s3",
                updated_at=1000000,
                spawned_by="agent:main:session1"
            ),
        }
        
        save_session_store(str(store_path), store)
        
        # List all
        opts = SessionsListOptions()
        result = list_sessions_from_store(str(store_path), store, opts)
        assert result.count == 3
        
        # Filter by label
        opts_label = SessionsListOptions(label="Label A")
        result_label = list_sessions_from_store(str(store_path), store, opts_label)
        assert result_label.count == 1
        assert result_label.sessions[0].session_id == "s1"
        
        # Filter by spawned_by
        opts_spawned = SessionsListOptions(spawned_by="agent:main:session1")
        result_spawned = list_sessions_from_store(str(store_path), store, opts_spawned)
        assert result_spawned.count == 1
        assert result_spawned.sessions[0].session_id == "s3"
        
        # Search
        opts_search = SessionsListOptions(search="Label B")
        result_search = list_sessions_from_store(str(store_path), store, opts_search)
        assert result_search.count == 1
        
        # Limit
        opts_limit = SessionsListOptions(limit=2)
        result_limit = list_sessions_from_store(str(store_path), store, opts_limit)
        assert result_limit.count == 2


def test_list_sessions_sorting():
    """Test that sessions are sorted by updated_at (newest first)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "sessions.json"
        
        store = {
            "s1": SessionEntry(session_id="s1", updated_at=1000000),
            "s2": SessionEntry(session_id="s2", updated_at=3000000),
            "s3": SessionEntry(session_id="s3", updated_at=2000000),
        }
        
        save_session_store(str(store_path), store)
        
        result = list_sessions_from_store(str(store_path), store, SessionsListOptions())
        
        # Should be sorted newest first
        assert result.sessions[0].session_id == "s2"  # 3000000
        assert result.sessions[1].session_id == "s3"  # 2000000
        assert result.sessions[2].session_id == "s1"  # 1000000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
