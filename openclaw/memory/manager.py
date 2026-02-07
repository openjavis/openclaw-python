"""
Memory search manager implementation

Matches TypeScript src/memory/manager.ts (simplified)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .types import (
    MemoryEmbeddingProbeResult,
    MemoryProviderStatus,
    MemorySearchResult,
    MemorySource,
)

logger = logging.getLogger(__name__)


class MemorySearchManager:
    """
    Simple memory search manager (matches TS MemorySearchManager interface).

    This is a simplified implementation that reads MEMORY.md and memory/*.md files
    and performs basic text search. For production, consider implementing:
    - Vector embeddings (using sentence-transformers or similar)
    - SQLite FTS (full-text search)
    - Chunking and indexing
    """

    def __init__(self, workspace_dir: Path, config: Any | None = None):
        """
        Initialize memory manager.

        Args:
            workspace_dir: Workspace directory
            config: OpenClaw configuration
        """
        self.workspace_dir = workspace_dir
        self.config = config
        self._memory_files: list[Path] = []
        self._indexed = False

    async def search(
        self, query: str, opts: dict[str, Any] | None = None
    ) -> list[MemorySearchResult]:
        """
        Search memory for query (matches TS interface).

        Args:
            query: Search query
            opts: Options (maxResults, minScore, sessionKey)

        Returns:
            List of search results
        """
        if not self._indexed:
            await self._index_files()

        opts = opts or {}
        max_results = opts.get("maxResults", 10)
        min_score = opts.get("minScore", 0.0)

        results = []
        query_lower = query.lower()

        # Simple text search through memory files
        for file_path in self._memory_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Simple scoring based on exact match
                        score = 1.0 if query.lower() == line.lower().strip() else 0.5

                        if score >= min_score:
                            # Get context (line +/- 2)
                            start_idx = max(0, i - 2)
                            end_idx = min(len(lines), i + 3)
                            snippet_lines = lines[start_idx:end_idx]
                            snippet = "\n".join(snippet_lines)

                            rel_path = file_path.relative_to(self.workspace_dir)

                            results.append(
                                MemorySearchResult(
                                    path=str(rel_path),
                                    start_line=start_idx + 1,  # 1-indexed
                                    end_line=end_idx,
                                    score=score,
                                    snippet=snippet,
                                    source=MemorySource.MEMORY,
                                )
                            )

            except Exception as e:
                logger.warning(f"Failed to search {file_path}: {e}")

        # Sort by score and limit
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    async def read_file(self, params: dict[str, Any]) -> dict[str, str]:
        """
        Read file from memory (matches TS interface).

        Args:
            params: Parameters (relPath, from, lines)

        Returns:
            dict with 'text' and 'path'
        """
        rel_path = params.get("relPath", "")
        from_line = params.get("from")
        lines_count = params.get("lines")

        file_path = self.workspace_dir / rel_path

        if not file_path.exists():
            return {"path": rel_path, "text": "", "error": "File not found"}

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            if from_line is not None:
                # 1-indexed to 0-indexed
                start = max(0, from_line - 1)
                if lines_count is not None:
                    end = min(len(lines), start + lines_count)
                    lines = lines[start:end]
                else:
                    lines = lines[start:]

            text = "\n".join(lines)
            return {"path": rel_path, "text": text}

        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return {"path": rel_path, "text": "", "error": str(e)}

    def status(self) -> MemoryProviderStatus:
        """Get memory provider status (matches TS interface)."""
        return MemoryProviderStatus(
            backend="builtin",
            provider="simple-text-search",
            files=len(self._memory_files),
            workspace_dir=str(self.workspace_dir),
        )

    async def sync(self, params: dict[str, Any] | None = None) -> None:
        """
        Sync memory index (matches TS interface).

        Args:
            params: Sync parameters (reason, force, progress callback)
        """
        await self._index_files()

    async def probe_embedding_availability(self) -> MemoryEmbeddingProbeResult:
        """Probe embedding model availability (matches TS interface)."""
        # Simple implementation always returns unavailable
        return MemoryEmbeddingProbeResult(
            ok=False, error="Embeddings not configured (simple text search only)"
        )

    async def probe_vector_availability(self) -> bool:
        """Probe vector database availability (matches TS interface)."""
        return False

    async def close(self) -> None:
        """Close and cleanup resources (matches TS interface)."""
        self._memory_files = []
        self._indexed = False

    async def _index_files(self) -> None:
        """Index memory files."""
        self._memory_files = []

        # Index MEMORY.md
        memory_file = self.workspace_dir / "MEMORY.md"
        if memory_file.exists():
            self._memory_files.append(memory_file)

        # Index memory/*.md
        memory_dir = self.workspace_dir / "memory"
        if memory_dir.exists() and memory_dir.is_dir():
            for file in memory_dir.glob("*.md"):
                if file.is_file():
                    self._memory_files.append(file)

        self._indexed = True
        logger.info(f"Indexed {len(self._memory_files)} memory files")


async def get_memory_search_manager(
    workspace_dir: Path, config: Any | None = None
) -> MemorySearchManager:
    """
    Get memory search manager (matches TS getMemorySearchManager pattern).

    Args:
        workspace_dir: Workspace directory
        config: OpenClaw configuration

    Returns:
        Memory search manager
    """
    manager = MemorySearchManager(workspace_dir, config)
    await manager.sync()
    return manager


# Backwards-compatible alias expected by tests
SimpleMemorySearchManager = MemorySearchManager
