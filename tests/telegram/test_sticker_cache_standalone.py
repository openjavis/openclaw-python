"""Standalone tests for sticker_cache module."""

import pytest
import tempfile
import json
import sys
from pathlib import Path
from unittest.mock import patch

# Add openclaw to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.telegram import sticker_cache


class TestCachedSticker:
    """Test CachedSticker dataclass."""
    
    def test_create_sticker(self):
        """Test creating a sticker."""
        sticker = sticker_cache.CachedSticker(
            file_id="file_123",
            file_unique_id="unique_123",
            emoji="😀",
            description="Happy face"
        )
        assert sticker.file_id == "file_123"
        assert sticker.emoji == "😀"


class TestStickerCache:
    """Test StickerCache class."""
    
    def test_empty_cache(self):
        """Test empty cache."""
        cache = sticker_cache.StickerCache()
        assert cache.version == 1
        assert len(cache.stickers) == 0
    
    def test_add_sticker_to_cache(self):
        """Test adding sticker to cache."""
        cache = sticker_cache.StickerCache()
        sticker = sticker_cache.CachedSticker(
            file_id="file_1",
            file_unique_id="unique_1",
            description="Test sticker"
        )
        cache.stickers["unique_1"] = sticker
        
        assert len(cache.stickers) == 1
    
    def test_to_dict(self):
        """Test converting cache to dict."""
        cache = sticker_cache.StickerCache()
        sticker = sticker_cache.CachedSticker(
            file_id="file_1",
            file_unique_id="unique_1",
            description="Test"
        )
        cache.stickers["unique_1"] = sticker
        
        data = cache.to_dict()
        assert "version" in data
        assert "stickers" in data


class TestCacheOperations:
    """Test caching and searching operations."""
    
    def test_cache_new_sticker(self):
        """Test caching a new sticker."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "sticker-cache.json"
            
            with patch.object(sticker_cache, "CACHE_FILE", cache_file):
                sticker = sticker_cache.CachedSticker(
                    file_id="file_1",
                    file_unique_id="unique_1",
                    description="New sticker"
                )
                sticker_cache.cache_sticker(sticker)
                
                # Verify it was saved
                assert cache_file.exists()
                data = json.loads(cache_file.read_text())
                assert "unique_1" in data["stickers"]
    
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
            
            with patch.object(sticker_cache, "CACHE_FILE", cache_file):
                results = sticker_cache.search_stickers("happy")
                assert len(results) >= 1
                assert any("Happy" in r.description for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
