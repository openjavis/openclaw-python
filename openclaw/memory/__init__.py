"""
Memory system for OpenClaw

Semantic search over MEMORY.md and session transcripts.
Matches TypeScript src/memory/
"""
from .manager import SimpleMemorySearchManager as MemorySearchManager
from .types import MemorySearchResult, MemorySource

__all__ = [
    "MemorySearchManager",
    "MemorySearchResult",
    "MemorySource",
]
