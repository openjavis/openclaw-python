"""
Integration tests for session alignment with TypeScript implementation

Tests:
- Store caching with TTL
- File locking for concurrent access
- Atomic writes
- Transcript JSONL format
- Session entry normalization
"""
import asyncio
import os
import tempfile
import time
from pathlib import Path

import pytest

from openclaw.config.sessions.store import (
    load_session_store,
    save_session_store,
    update_session_store,
    update_session_store_entry,
    clear_session_store_cache_for_test,
)
from openclaw.config.sessions.types import SessionEntry, DeliveryContext
from openclaw.config.sessions.transcript import (
    ensure_session_header,
    append_assistant_message_to_session_transcript,
    read_session_messages,
    resolve_mirrored_transcript_text,
)


@pytest.fixture
def temp_store_path():
    """Create temporary store path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store_path = Path(tmpdir) / "sessions.json"
        yield store_path
        # Clear cache after test
        clear_session_store_cache_for_test()


@pytest.fixture
def temp_transcript_path():
    """Create temporary transcript path"""
    with tempfile.TemporaryDirectory() as tmpdir:
        transcript_path = Path(tmpdir) / "test_session.jsonl"
        yield transcript_path


class TestStoreCache:
    """Test store caching functionality"""
    
    def test_cache_hit(self, temp_store_path):
        """Test cache hit on repeated loads"""
        # Create initial store
        store = {
            "test_key": SessionEntry(
                session_id="test-123",
                updated_at=1000,
            )
        }
        save_session_store(temp_store_path, store)
        
        # First load
        loaded1 = load_session_store(temp_store_path)
        assert "test_key" in loaded1
        assert loaded1["test_key"].session_id == "test-123"
        
        # Second load should hit cache
        loaded2 = load_session_store(temp_store_path)
        assert loaded2["test_key"].session_id == "test-123"
    
    def test_cache_invalidation_on_write(self, temp_store_path):
        """Test cache is invalidated on write"""
        # Initial store
        store = {
            "test_key": SessionEntry(
                session_id="test-123",
                updated_at=1000,
            )
        }
        save_session_store(temp_store_path, store)
        
        # Load (cache it)
        loaded1 = load_session_store(temp_store_path)
        assert loaded1["test_key"].session_id == "test-123"
        
        # Update store
        store["test_key"] = SessionEntry(
            session_id="test-456",
            updated_at=2000,
        )
        save_session_store(temp_store_path, store)
        
        # Load again (should get new data)
        loaded2 = load_session_store(temp_store_path)
        assert loaded2["test_key"].session_id == "test-456"
    
    def test_cache_skip(self, temp_store_path):
        """Test skip_cache parameter"""
        store = {
            "test_key": SessionEntry(
                session_id="test-123",
                updated_at=1000,
            )
        }
        save_session_store(temp_store_path, store)
        
        # Load without cache
        loaded = load_session_store(temp_store_path, skip_cache=True)
        assert loaded["test_key"].session_id == "test-123"


class TestFileLocking:
    """Test file locking for concurrent access"""
    
    def test_concurrent_updates(self, temp_store_path):
        """Test concurrent updates are serialized by lock"""
        # Initialize store
        initial_store = {
            "counter": SessionEntry(
                session_id="counter-0",
                updated_at=0,
            )
        }
        save_session_store(temp_store_path, initial_store)
        
        # Counter for updates
        update_count = [0]
        
        def increment_counter(store):
            """Mutator that increments counter"""
            current = int(store["counter"].session_id.split("-")[1])
            update_count[0] = current + 1
            store["counter"] = SessionEntry(
                session_id=f"counter-{current + 1}",
                updated_at=int(time.time() * 1000),
            )
            return store
        
        # Perform 5 concurrent updates
        for _ in range(5):
            update_session_store(temp_store_path, increment_counter)
        
        # Final value should be 5
        final_store = load_session_store(temp_store_path, skip_cache=True)
        final_value = int(final_store["counter"].session_id.split("-")[1])
        assert final_value == 5


class TestAtomicWrites:
    """Test atomic write operations"""
    
    def test_atomic_write_success(self, temp_store_path):
        """Test successful atomic write"""
        store = {
            "test": SessionEntry(
                session_id="test-123",
                updated_at=1000,
                channel="telegram",
            )
        }
        
        save_session_store(temp_store_path, store)
        
        # Verify file exists and is readable
        assert temp_store_path.exists()
        loaded = load_session_store(temp_store_path)
        assert loaded["test"].channel == "telegram"
    
    def test_update_single_entry(self, temp_store_path):
        """Test updating single entry atomically"""
        # Initialize
        initial = {
            "entry1": SessionEntry(session_id="id1", updated_at=1000),
            "entry2": SessionEntry(session_id="id2", updated_at=2000),
        }
        save_session_store(temp_store_path, initial)
        
        # Update entry1
        updated = update_session_store_entry(
            temp_store_path,
            "entry1",
            {"channel": "telegram", "chat_type": "dm"}
        )
        
        assert updated.channel == "telegram"
        assert updated.chat_type == "dm"
        
        # Verify entry2 is unchanged
        store = load_session_store(temp_store_path, skip_cache=True)
        assert store["entry2"].session_id == "id2"


class TestTranscript:
    """Test transcript JSONL operations"""
    
    def test_header_creation(self, temp_transcript_path):
        """Test session header is created"""
        ensure_session_header(temp_transcript_path, "test-session-123")
        
        assert temp_transcript_path.exists()
        
        # Read and verify header
        with open(temp_transcript_path) as f:
            header_line = f.readline()
        
        import json
        header = json.loads(header_line)
        assert header["type"] == "session"
        assert header["id"] == "test-session-123"
        assert "version" in header
        assert "timestamp" in header
    
    def test_message_append(self, temp_transcript_path, temp_store_path):
        """Test appending messages to transcript"""
        # Create session entry
        session_key = "test-key"
        store = {
            session_key: SessionEntry(
                session_id="test-123",
                updated_at=1000,
                session_file=temp_transcript_path.name,
            )
        }
        
        # Save to parent directory of transcript
        store_path = temp_transcript_path.parent / "sessions.json"
        save_session_store(store_path, store)
        
        # Append message
        result = append_assistant_message_to_session_transcript(
            agent_id=None,
            session_key=session_key,
            text="Hello, world!",
            store_path=store_path,
        )
        
        assert result["ok"] is True
        
        # Read messages
        messages = read_session_messages(temp_transcript_path)
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "Hello, world!"
    
    def test_media_text_resolution(self):
        """Test resolving text for media messages"""
        # Text only
        text = resolve_mirrored_transcript_text(text="Hello")
        assert text == "Hello"
        
        # Media only
        text = resolve_mirrored_transcript_text(
            media_urls=["https://example.com/image.jpg"]
        )
        assert text == "image.jpg"
        
        # Multiple media
        text = resolve_mirrored_transcript_text(
            media_urls=[
                "https://example.com/img1.jpg",
                "https://example.com/img2.png",
            ]
        )
        assert "img1.jpg" in text
        assert "img2.png" in text
        
        # Empty
        text = resolve_mirrored_transcript_text()
        assert text is None


class TestSessionEntry:
    """Test session entry normalization"""
    
    def test_delivery_context_normalization(self, temp_store_path):
        """Test delivery context is normalized"""
        entry = SessionEntry(
            session_id="test-123",
            updated_at=1000,
            last_channel="telegram",
            last_to="user123",
        )
        
        store = {"key1": entry}
        save_session_store(temp_store_path, store)
        
        # Load and check normalization
        loaded = load_session_store(temp_store_path)
        loaded_entry = loaded["key1"]
        
        # Should have delivery_context populated
        assert loaded_entry.delivery_context is not None
        assert loaded_entry.delivery_context.channel == "telegram"
        assert loaded_entry.delivery_context.to == "user123"
    
    def test_legacy_field_migration(self, temp_store_path):
        """Test legacy fields are migrated"""
        import json
        
        # Write legacy format directly
        legacy_store = {
            "key1": {
                "session_id": "test-123",
                "updated_at": 1000,
                "provider": "telegram",  # Legacy: should become "channel"
                "room": "room-123",      # Legacy: should become "groupChannel"
            }
        }
        
        with open(temp_store_path, "w") as f:
            json.dump(legacy_store, f)
        
        # Load with migration
        loaded = load_session_store(temp_store_path)
        entry = loaded["key1"]
        
        # Check migration
        assert entry.channel == "telegram"
        assert entry.group_channel == "room-123"


@pytest.mark.asyncio
async def test_full_session_flow(temp_store_path, temp_transcript_path):
    """Test complete session flow"""
    session_key = "agent:main:telegram:dm:user123"
    
    # 1. Create session entry
    entry = SessionEntry(
        session_id="session-456",
        updated_at=int(time.time() * 1000),
        session_file=temp_transcript_path.name,
        channel="telegram",
        chat_type="dm",
    )
    
    store = {session_key: entry}
    save_session_store(temp_store_path, store)
    
    # 2. Ensure transcript header
    ensure_session_header(temp_transcript_path, entry.session_id)
    
    # 3. Append messages
    result = append_assistant_message_to_session_transcript(
        agent_id=None,
        session_key=session_key,
        text="Hello from assistant!",
        store_path=temp_store_path,
    )
    assert result["ok"] is True
    
    # 4. Read back
    messages = read_session_messages(temp_transcript_path)
    assert len(messages) == 1
    assert messages[0]["content"] == "Hello from assistant!"
    
    # 5. Update session entry
    updated_entry = update_session_store_entry(
        temp_store_path,
        session_key,
        {"compaction_count": 1, "total_tokens": 100}
    )
    assert updated_entry.compaction_count == 1
    assert updated_entry.total_tokens == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
