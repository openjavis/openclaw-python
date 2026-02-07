"""
Memory system types

Matches TypeScript src/memory/types.ts
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class MemorySource(str, Enum):
    """Memory source type (matches TS MemorySource)."""

    MEMORY = "memory"
    SESSIONS = "sessions"


@dataclass
class MemorySearchResult:
    """
    Memory search result (matches TS MemorySearchResult).

    Attributes:
        path: Relative file path
        start_line: Start line number (1-indexed)
        end_line: End line number (1-indexed)
        score: Search score (0-1)
        snippet: Text snippet
        source: Source type (memory | sessions)
        citation: Optional citation string
    """

    path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    source: MemorySource
    citation: str | None = None


@dataclass
class MemoryEmbeddingProbeResult:
    """Embedding availability probe result (matches TS)."""

    ok: bool
    error: str | None = None


@dataclass
class MemorySyncProgressUpdate:
    """Sync progress update (matches TS)."""

    completed: int
    total: int
    label: str | None = None


@dataclass
class MemoryProviderStatus:
    """
    Memory provider status (matches TS MemoryProviderStatus).

    Comprehensive status information about the memory backend.
    """

    backend: str  # "builtin" | "qmd"
    provider: str
    model: str | None = None
    requested_provider: str | None = None
    files: int | None = None
    chunks: int | None = None
    dirty: bool = False
    workspace_dir: str | None = None
    db_path: str | None = None
    extra_paths: list[str] | None = None
    sources: list[MemorySource] | None = None
    source_counts: list[dict[str, Any]] | None = None
    cache: dict[str, Any] | None = None
    fts: dict[str, Any] | None = None
    fallback: dict[str, str] | None = None
    vector: dict[str, Any] | None = None
    batch: dict[str, Any] | None = None
    custom: dict[str, Any] | None = None


class MemorySearchManager(Protocol):
    """
    Memory search manager interface (matches TS MemorySearchManager).

    Protocol for memory search implementations.
    """

    async def search(
        self, query: str, opts: dict[str, Any] | None = None
    ) -> list[MemorySearchResult]:
        """
        Search memory for query.

        Args:
            query: Search query
            opts: Options (maxResults, minScore, sessionKey)

        Returns:
            List of search results
        """
        ...

    async def read_file(self, params: dict[str, Any]) -> dict[str, str]:
        """
        Read file from memory.

        Args:
            params: Parameters (relPath, from, lines)

        Returns:
            dict with 'text' and 'path'
        """
        ...

    def status(self) -> MemoryProviderStatus:
        """Get memory provider status."""
        ...

    async def sync(self, params: dict[str, Any] | None = None) -> None:
        """
        Sync memory index.

        Args:
            params: Sync parameters (reason, force, progress callback)
        """
        ...

    async def probe_embedding_availability(self) -> MemoryEmbeddingProbeResult:
        """Probe embedding model availability."""
        ...

    async def probe_vector_availability(self) -> bool:
        """Probe vector database availability."""
        ...

    async def close(self) -> None:
        """Close and cleanup resources."""
        ...


@dataclass
class MemorySearchOptions:
    """Options for memory search."""

    max_results: int = 10
    min_score: float = 0.0
    session_key: str | None = None
    include_sessions: bool = False


@dataclass
class MemoryReadFileParams:
    """Parameters for reading memory file."""

    rel_path: str
    from_line: int | None = None
    lines: int | None = None
