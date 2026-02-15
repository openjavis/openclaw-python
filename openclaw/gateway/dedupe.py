"""
Request deduplication manager - aligned with openclaw-ts server-shared.ts

Provides idempotency support for chat requests through result caching.
"""
from __future__ import annotations

import asyncio
import time
import logging
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger(__name__)


@dataclass
class DedupeEntry:
    """
    Deduplication cache entry - aligned with openclaw-ts DedupeEntry
    
    Caches request results for idempotency support
    """
    ts: float  # Timestamp in milliseconds
    ok: bool   # Success flag
    payload: Any | None = None  # Success payload
    error: dict | None = None   # Error payload


class DedupeManager:
    """
    Idempotency deduplication manager - aligned with openclaw-ts dedupe
    
    Caches request results by idempotency key to support:
    - Request retries with same result
    - Network failure recovery
    - Client-side deduplication
    
    Features:
    - 60 second TTL for entries
    - Maximum 1000 entries (LRU eviction)
    - Automatic cleanup of expired entries
    """
    
    DEDUPE_TTL_MS = 60_000  # 60 seconds - aligned with openclaw-ts
    DEDUPE_MAX = 1000       # Maximum entries - aligned with openclaw-ts
    
    def __init__(self, ttl_ms: int = DEDUPE_TTL_MS, max_entries: int = DEDUPE_MAX):
        """
        Initialize dedupe manager
        
        Args:
            ttl_ms: Time-to-live in milliseconds
            max_entries: Maximum number of entries
        """
        self.ttl_ms = ttl_ms
        self.max_entries = max_entries
        self._cache: Dict[str, DedupeEntry] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> DedupeEntry | None:
        """
        Get cached result for idempotency key
        
        Args:
            key: Idempotency key
            
        Returns:
            Cached entry if found and not expired, None otherwise
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if not entry:
                return None
            
            # Check if expired
            now = time.time() * 1000
            if (now - entry.ts) > self.ttl_ms:
                # Expired, remove it
                del self._cache[key]
                logger.debug(f"Dedupe entry expired for key: {key}")
                return None
            
            logger.debug(f"Dedupe cache hit for key: {key}")
            return entry
    
    async def set(self, key: str, entry: DedupeEntry) -> None:
        """
        Set cached result for idempotency key
        
        Args:
            key: Idempotency key
            entry: Entry to cache
        """
        async with self._lock:
            self._cache[key] = entry
            logger.debug(f"Cached dedupe entry for key: {key}")
            
            # Check if cleanup needed
            if len(self._cache) > self.max_entries:
                await self._cleanup_internal()
    
    async def delete(self, key: str) -> bool:
        """
        Delete cached entry
        
        Args:
            key: Idempotency key
            
        Returns:
            True if entry was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted dedupe entry for key: {key}")
                return True
            return False
    
    async def cleanup(self) -> int:
        """
        Cleanup expired and excess entries - aligned with openclaw-ts
        
        Removes:
        1. Expired entries (older than TTL)
        2. Oldest entries if count exceeds max
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            return await self._cleanup_internal()
    
    async def _cleanup_internal(self) -> int:
        """Internal cleanup (must hold lock)"""
        now = time.time() * 1000
        removed_count = 0
        
        # 1. Remove expired entries
        expired_keys = [
            k for k, v in self._cache.items()
            if (now - v.ts) > self.ttl_ms
        ]
        for k in expired_keys:
            del self._cache[k]
            removed_count += 1
        
        if expired_keys:
            logger.debug(f"Removed {len(expired_keys)} expired dedupe entries")
        
        # 2. If still over limit, remove oldest entries
        if len(self._cache) > self.max_entries:
            # Sort by timestamp (oldest first)
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].ts
            )
            
            # Calculate how many to remove
            to_remove = len(self._cache) - self.max_entries
            
            # Remove oldest entries
            for k, _ in sorted_entries[:to_remove]:
                del self._cache[k]
                removed_count += 1
            
            logger.info(f"Removed {to_remove} oldest dedupe entries (limit={self.max_entries})")
        
        return removed_count
    
    async def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        async with self._lock:
            now = time.time() * 1000
            total = len(self._cache)
            expired = sum(
                1 for v in self._cache.values()
                if (now - v.ts) > self.ttl_ms
            )
            
            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "ttl_ms": self.ttl_ms,
                "max_entries": self.max_entries,
            }
