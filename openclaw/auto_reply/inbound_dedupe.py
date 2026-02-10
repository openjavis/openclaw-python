"""Inbound message deduplication

Prevents duplicate processing of messages using:
- In-memory LRU cache
- Message hash tracking
- Configurable TTL
"""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Optional

from .envelope import InboundEnvelope

logger = logging.getLogger(__name__)


class InboundDedupe:
    """
    Deduplication manager for inbound messages
    
    Uses LRU cache with configurable size and TTL.
    """
    
    def __init__(self, max_size: int = 1000, ttl: float = 3600.0):
        """
        Initialize dedupe manager
        
        Args:
            max_size: Maximum cache size
            ttl: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        
        # Cache: message_hash -> timestamp
        self._cache: OrderedDict[str, float] = OrderedDict()
    
    def is_duplicate(self, envelope: InboundEnvelope) -> bool:
        """
        Check if message is duplicate
        
        Args:
            envelope: Message envelope
            
        Returns:
            True if duplicate
        """
        message_hash = envelope.message_hash
        
        # Check cache
        if message_hash in self._cache:
            # Check TTL
            cached_time = self._cache[message_hash]
            age = time.time() - cached_time
            
            if age < self.ttl:
                logger.debug(f"Duplicate message detected: {message_hash}")
                
                # Move to end (LRU)
                self._cache.move_to_end(message_hash)
                
                return True
            else:
                # Expired, remove
                del self._cache[message_hash]
        
        # Not duplicate, add to cache
        self._add_to_cache(message_hash)
        
        return False
    
    def _add_to_cache(self, message_hash: str) -> None:
        """Add message hash to cache"""
        current_time = time.time()
        
        # Add to cache
        self._cache[message_hash] = current_time
        
        # Enforce max size (LRU eviction)
        while len(self._cache) > self.max_size:
            # Remove oldest
            self._cache.popitem(last=False)
    
    def clear_expired(self) -> int:
        """
        Clear expired entries
        
        Returns:
            Number of entries cleared
        """
        current_time = time.time()
        expired = []
        
        for message_hash, timestamp in self._cache.items():
            age = current_time - timestamp
            if age >= self.ttl:
                expired.append(message_hash)
        
        for message_hash in expired:
            del self._cache[message_hash]
        
        if expired:
            logger.debug(f"Cleared {len(expired)} expired dedup entries")
        
        return len(expired)
    
    def clear(self) -> None:
        """Clear all entries"""
        self._cache.clear()
        logger.debug("Cleared all dedup entries")
    
    def get_stats(self) -> dict[str, int]:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
        }


# Global dedupe instance
_global_dedupe: Optional[InboundDedupe] = None


def get_global_dedupe() -> InboundDedupe:
    """Get or create global dedupe instance"""
    global _global_dedupe
    
    if _global_dedupe is None:
        _global_dedupe = InboundDedupe()
    
    return _global_dedupe


def is_duplicate_message(envelope: InboundEnvelope) -> bool:
    """
    Check if message is duplicate (convenience function)
    
    Args:
        envelope: Message envelope
        
    Returns:
        True if duplicate
    """
    dedupe = get_global_dedupe()
    return dedupe.is_duplicate(envelope)
