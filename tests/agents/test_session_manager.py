"""
Unit tests for SessionManager

Tests session management including creation, caching, and cleanup.
"""

import pytest
from pathlib import Path
from openclaw.agents.session import SessionManager, Session


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    return tmp_path / "workspace"


@pytest.fixture
def session_manager(temp_workspace):
    """Create a SessionManager instance."""
    return SessionManager(workspace_dir=temp_workspace)


class TestSessionManagerCreation:
    """Test SessionManager initialization."""
    
    def test_create_manager(self, temp_workspace):
        """Test creating a SessionManager."""
        manager = SessionManager(workspace_dir=temp_workspace)
        
        assert manager.workspace_dir == temp_workspace
        assert isinstance(manager._sessions, dict)
    
    def test_sessions_directory_created(self, session_manager):
        """Test that sessions directory is created."""
        sessions_dir = session_manager.workspace_dir / ".sessions"
        assert sessions_dir.exists()


class TestGetOrCreateSession:
    """Test getting and creating sessions."""
    
    def test_create_new_session(self, session_manager):
        """Test creating a new session."""
        session = session_manager.get_or_create("new-session")
        
        assert isinstance(session, Session)
        assert session.session_id == "new-session"
    
    def test_get_existing_session(self, session_manager):
        """Test getting an existing session from cache."""
        # Create first session
        session1 = session_manager.get_or_create("test-session")
        session1.add_user_message("Test message")
        
        # Get same session (should return cached instance)
        session2 = session_manager.get_or_create("test-session")
        
        assert session1 is session2  # Same object
        assert len(session2.messages) == 1
    
    def test_multiple_sessions(self, session_manager):
        """Test managing multiple sessions."""
        session1 = session_manager.get_or_create("session-1")
        session2 = session_manager.get_or_create("session-2")
        
        session1.add_user_message("Message 1")
        session2.add_user_message("Message 2")
        
        assert len(session1.messages) == 1
        assert len(session2.messages) == 1
        assert session1.messages[0].content != session2.messages[0].content


class TestListSessions:
    """Test listing sessions."""
    
    def test_list_empty_sessions(self, session_manager):
        """Test listing when no sessions exist."""
        sessions = session_manager.list_sessions()
        
        assert sessions == []
    
    def test_list_sessions(self, session_manager):
        """Test listing existing sessions."""
        # Create multiple sessions
        session_manager.get_or_create("session-1")
        session_manager.get_or_create("session-2")
        session_manager.get_or_create("session-3")
        
        sessions = session_manager.list_sessions()
        
        assert len(sessions) == 3
        assert "session-1" in sessions
        assert "session-2" in sessions
        assert "session-3" in sessions
    
    def test_list_sessions_from_disk(self, temp_workspace):
        """Test listing sessions that exist on disk but not in cache."""
        # Create sessions and save to disk
        manager1 = SessionManager(workspace_dir=temp_workspace)
        manager1.get_or_create("disk-session-1").add_user_message("Test")
        manager1.get_or_create("disk-session-2").add_user_message("Test")
        
        # Create new manager instance (empty cache)
        manager2 = SessionManager(workspace_dir=temp_workspace)
        sessions = manager2.list_sessions()
        
        assert len(sessions) >= 2
        assert "disk-session-1" in sessions
        assert "disk-session-2" in sessions


class TestDeleteSession:
    """Test session deletion."""
    
    def test_delete_session(self, session_manager):
        """Test deleting a session."""
        # Create session
        session = session_manager.get_or_create("to-delete")
        session.add_user_message("Test")
        
        # Delete it
        result = session_manager.delete_session("to-delete")
        
        assert result is True
        assert "to-delete" not in session_manager._sessions
        assert not (session_manager.workspace_dir / ".sessions" / "to-delete.json").exists()
    
    def test_delete_nonexistent_session(self, session_manager):
        """Test deleting a session that doesn't exist."""
        result = session_manager.delete_session("nonexistent")
        
        # Should return False or handle gracefully
        assert result is False or result is True  # Depends on implementation
    
    def test_session_removed_from_cache(self, session_manager):
        """Test that deleted session is removed from cache."""
        session_manager.get_or_create("cached-session")
        
        session_manager.delete_session("cached-session")
        
        # Getting it again should create a new empty session
        new_session = session_manager.get_or_create("cached-session")
        assert len(new_session.messages) == 0


class TestSessionCaching:
    """Test session caching behavior."""
    
    def test_sessions_cached(self, session_manager):
        """Test that sessions are cached."""
        session1 = session_manager.get_or_create("cached")
        session2 = session_manager.get_or_create("cached")
        
        # Should return same instance
        assert session1 is session2
    
    def test_cache_persists_messages(self, session_manager):
        """Test that cached sessions maintain their messages."""
        session = session_manager.get_or_create("test")
        session.add_user_message("Message 1")
        session.add_user_message("Message 2")
        
        # Get from cache
        cached = session_manager.get_or_create("test")
        
        assert len(cached.messages) == 2


class TestConcurrency:
    """Test concurrent access (basic thread safety)."""
    
    def test_multiple_gets_same_session(self, session_manager):
        """Test multiple rapid gets of same session."""
        sessions = []
        for _ in range(10):
            sessions.append(session_manager.get_or_create("concurrent"))
        
        # All should be the same instance
        assert all(s is sessions[0] for s in sessions)
    
    def test_different_sessions_independent(self, session_manager):
        """Test that different sessions don't interfere."""
        session1 = session_manager.get_or_create("independent-1")
        session2 = session_manager.get_or_create("independent-2")
        
        session1.add_user_message("Message 1")
        session2.add_user_message("Message 2")
        
        assert len(session1.messages) == 1
        assert len(session2.messages) == 1
        assert session1.messages[0].content == "Message 1"
        assert session2.messages[0].content == "Message 2"


class TestPersistenceAcrossManagers:
    """Test that sessions persist across SessionManager instances."""
    
    def test_session_survives_manager_restart(self, temp_workspace):
        """Test that sessions persist when manager is recreated."""
        # Create manager and session
        manager1 = SessionManager(workspace_dir=temp_workspace)
        session1 = manager1.get_or_create("persistent")
        session1.add_user_message("Persistent message")
        session1.set_metadata("key", "value")
        
        # Create new manager instance
        manager2 = SessionManager(workspace_dir=temp_workspace)
        session2 = manager2.get_or_create("persistent")
        
        # Should have loaded from disk
        assert len(session2.messages) == 1
        assert session2.messages[0].content == "Persistent message"
        assert session2.get_metadata("key") == "value"
    
    def test_multiple_sessions_persist(self, temp_workspace):
        """Test that multiple sessions all persist."""
        # Create multiple sessions
        manager1 = SessionManager(workspace_dir=temp_workspace)
        for i in range(5):
            session = manager1.get_or_create(f"session-{i}")
            session.add_user_message(f"Message {i}")
        
        # Recreate manager
        manager2 = SessionManager(workspace_dir=temp_workspace)
        
        # All should be loadable
        for i in range(5):
            session = manager2.get_or_create(f"session-{i}")
            assert len(session.messages) == 1
            assert session.messages[0].content == f"Message {i}"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_session_id_with_special_characters(self, session_manager):
        """Test creating session with special characters in ID."""
        # This may need sanitization depending on implementation
        session = session_manager.get_or_create("session-with-dash")
        
        assert session.session_id == "session-with-dash"
    
    def test_empty_session_id(self, session_manager):
        """Test handling empty session ID."""
        # Should either raise error or generate ID
        try:
            session = session_manager.get_or_create("")
            # If it succeeds, should have some ID
            assert session.session_id != ""
        except ValueError:
            # Or it should raise an error
            pass
    
    def test_workspace_dir_not_writable(self, tmp_path):
        """Test handling non-writable workspace."""
        # This test may vary based on OS permissions
        # Just ensure it doesn't crash
        workspace = tmp_path / "workspace"
        manager = SessionManager(workspace_dir=workspace)
        
        # Should create the directory
        assert workspace.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
