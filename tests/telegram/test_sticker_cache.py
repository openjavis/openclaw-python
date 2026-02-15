"""Unit tests for openclaw.telegram.sticker_cache module.

Tests sticker caching and search functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from openclaw.telegram.sticker_cache import (
    CachedSticker,
    StickerCache,
    get_cached_sticker,
    cache_sticker,
    search_stickers,
)


class TestCachedSticker:
    """Test CachedSticker dataclass."""
    
    def test_create_sticker(self):
        """Test creating a sticker."""
        sticker = CachedSticker(
            file_id="file_123",
            file_unique_id="unique_123",
            emoji="😀",
            description="Happy face"
        )
        assert sticker.file_id == "file_123"
        assert sticker.file_unique_id == "unique_123"
        assert sticker.emoji == "😀"
        assert sticker.description == "Happy face"


class TestStickerCache:
    """Test StickerCache class."""
    
    def test_empty_cache(self):
        """Test empty cache."""
        cache = StickerCache()
        assert cache.version == 1
        assert len(cache.stickers) == 0
    
    def test_add_sticker_to_cache(self):
        """Test adding sticker to cache."""
        cache = StickerCache()
        sticker = CachedSticker(
            file_id="file_1",
            file_unique_id="unique_1",
            description="Test sticker"
        )
        cache.stickers["unique_1"] = sticker
        
        assert len(cache.stickers) == 1
        assert cache.stickers["unique_1"].description == "Test sticker"
    
    def test_to_dict(self):
        """Test converting cache to dict."""
        cache = StickerCache()
        sticker = CachedSticker(
            file_id="file_1",
            file_unique_id="unique_1",
            description="Test"
        )
        cache.stickers["unique_1"] = sticker
        
        data = cache.to_dict()
        assert "version" in data
        assert "stickers" in data
        assert "unique_1" in data["stickers"]
    
    def test_from_dict(self):
        """Test creating cache from dict."""
        data = {
            "version": 1,
            "stickers": {
                "unique_1": {
                    "file_id": "file_1",
                    "file_unique_id": "unique_1",
                    "description": "Test"
                }
            }
        }
        cache = StickerCache.from_dict(data)
        
        assert cache.version == 1
        assert len(cache.stickers) == 1
        assert cache.stickers["unique_1"].description == "Test"


class TestGetCachedSticker:
    """Test get_cached_sticker function."""
    
    def test_get_nonexistent_sticker(self):
        """Test getting non-existent sticker returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                result = get_cached_sticker("nonexistent")
                assert result is None
    
    def test_get_existing_sticker(self):
        """Test getting existing sticker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            # Create cache with one sticker
            cache_data = {
                "version": 1,
                "stickers": {
                    "unique_1": {
                        "file_id": "file_1",
                        "file_unique_id": "unique_1",
                        "emoji": "😀",
                        "description": "Happy"
                    }
                }
            }
            cache_file.write_text(json.dumps(cache_data))
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                result = get_cached_sticker("unique_1")
                assert result is not None
                assert result.file_id == "file_1"
                assert result.description == "Happy"


class TestCacheSticker:
    """Test cache_sticker function."""
    
    def test_cache_new_sticker(self):
        """Test caching a new sticker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                sticker = CachedSticker(
                    file_id="file_1",
                    file_unique_id="unique_1",
                    description="New sticker"
                )
                cache_sticker(sticker)
                
                # Verify it was saved
                assert cache_file.exists()
                data = json.loads(cache_file.read_text())
                assert "unique_1" in data["stickers"]
                assert data["stickers"]["unique_1"]["description"] == "New sticker"
    
    def test_update_existing_sticker(self):
        """Test updating an existing sticker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            # Create initial cache
            initial_data = {
                "version": 1,
                "stickers": {
                    "unique_1": {
                        "file_id": "file_1",
                        "file_unique_id": "unique_1",
                        "description": "Old description"
                    }
                }
            }
            cache_file.write_text(json.dumps(initial_data))
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                # Update sticker
                sticker = CachedSticker(
                    file_id="file_1",
                    file_unique_id="unique_1",
                    description="New description"
                )
                cache_sticker(sticker)
                
                # Verify it was updated
                data = json.loads(cache_file.read_text())
                assert data["stickers"]["unique_1"]["description"] == "New description"


class TestSearchStickers:
    """Test search_stickers function."""
    
    def test_search_empty_cache(self):
        """Test searching empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                results = search_stickers("happy")
                assert len(results) == 0
    
    def test_search_by_description(self):
        """Test searching by description."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            # Create cache with stickers
            cache_data = {
                "version": 1,
                "stickers": {
                    "unique_1": {
                        "file_id": "file_1",
                        "file_unique_id": "unique_1",
                        "description": "Happy face emoji"
                    },
                    "unique_2": {
                        "file_id": "file_2",
                        "file_unique_id": "unique_2",
                        "description": "Sad face emoji"
                    }
                }
            }
            cache_file.write_text(json.dumps(cache_data))
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                results = search_stickers("happy")
                assert len(results) >= 1
                assert any("Happy" in r.description for r in results)
    
    def test_search_limit(self):
        """Test search limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            # Create cache with many matching stickers
            stickers = {}
            for i in range(20):
                stickers[f"unique_{i}"] = {
                    "file_id": f"file_{i}",
                    "file_unique_id": f"unique_{i}",
                    "description": f"Face emoji number {i}"
                }
            cache_data = {"version": 1, "stickers": stickers}
            cache_file.write_text(json.dumps(cache_data))
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                results = search_stickers("face", limit=5)
                assert len(results) <= 5
    
    def test_search_case_insensitive(self):
        """Test search is case insensitive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            cache_data = {
                "version": 1,
                "stickers": {
                    "unique_1": {
                        "file_id": "file_1",
                        "file_unique_id": "unique_1",
                        "description": "HAPPY Face"
                    }
                }
            }
            cache_file.write_text(json.dumps(cache_data))
            
            with patch("openclaw.telegram.sticker_cache.CACHE_FILE", cache_file):
                results = search_stickers("happy")
                assert len(results) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
