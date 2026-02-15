"""Sticker caching and search for Telegram.

Caches sticker descriptions for search functionality.
Matches TypeScript src/telegram/sticker-cache.ts
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CACHE_FILE = Path.home() / ".openclaw" / "state" / "telegram" / "sticker-cache.json"
CACHE_VERSION = 1


@dataclass
class CachedSticker:
    """Cached sticker information."""
    
    file_id: str
    file_unique_id: str
    emoji: Optional[str] = None
    set_name: Optional[str] = None
    description: str = ""
    cached_at: Optional[str] = None
    received_from: Optional[str] = None


class StickerCache:
    """Sticker cache storage."""
    
    def __init__(self):
        self.version = CACHE_VERSION
        self.stickers: dict[str, CachedSticker] = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "stickers": {k: asdict(v) for k, v in self.stickers.items()}
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StickerCache":
        """Create from dictionary."""
        cache = cls()
        cache.version = data.get("version", CACHE_VERSION)
        stickers_data = data.get("stickers", {})
        for key, sticker_dict in stickers_data.items():
            cache.stickers[key] = CachedSticker(**sticker_dict)
        return cache


def load_cache() -> StickerCache:
    """Load sticker cache from file."""
    if not CACHE_FILE.exists():
        return StickerCache()
    
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)
        return StickerCache.from_dict(data)
    except Exception as e:
        logger.warning(f"Failed to load sticker cache: {e}")
        return StickerCache()


def save_cache(cache: StickerCache):
    """Save sticker cache to file."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache.to_dict(), f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save sticker cache: {e}")


def get_cached_sticker(file_unique_id: str) -> Optional[CachedSticker]:
    """Get a cached sticker by unique ID."""
    cache = load_cache()
    return cache.stickers.get(file_unique_id)


def cache_sticker(sticker: CachedSticker):
    """Add or update a sticker in the cache."""
    cache = load_cache()
    if not sticker.cached_at:
        sticker.cached_at = datetime.utcnow().isoformat()
    cache.stickers[sticker.file_unique_id] = sticker
    save_cache(cache)


def search_stickers(query: str, limit: int = 10) -> list[CachedSticker]:
    """Search cached stickers by text query.
    
    Performs fuzzy matching on description, emoji, and set name.
    
    Args:
        query: Search query
        limit: Maximum results
    
    Returns:
        List of matching stickers
    """
    cache = load_cache()
    query_lower = query.lower()
    results: list[tuple[CachedSticker, float]] = []
    
    for sticker in cache.stickers.values():
        score = 0.0
        desc_lower = sticker.description.lower()
        
        # Exact match in description
        if query_lower in desc_lower:
            score += 10.0
        
        # Word match
        query_words = query_lower.split()
        desc_words = desc_lower.split()
        for qword in query_words:
            if any(qword in dword for dword in desc_words):
                score += 5.0
        
        # Emoji match
        if sticker.emoji and query_lower in sticker.emoji.lower():
            score += 3.0
        
        # Set name match
        if sticker.set_name and query_lower in sticker.set_name.lower():
            score += 2.0
        
        if score > 0:
            results.append((sticker, score))
    
    # Sort by score descending
    results.sort(key=lambda x: x[1], reverse=True)
    
    return [sticker for sticker, _ in results[:limit]]
