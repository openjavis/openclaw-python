"""Voyage AI embedding provider.

Matches TypeScript memory/embeddings/voyage.ts.
Voyage AI provides high-quality embeddings optimised for code and text retrieval.
"""
from __future__ import annotations

import logging
import os
from typing import List

from .base import EmbeddingBatch, EmbeddingProvider

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "voyage-3"
_DEFAULT_DIMENSIONS = 1024


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Voyage AI embedding provider.

    Requires:
    - VOYAGE_API_KEY environment variable, OR
    - api_key parameter passed at construction.

    Supports models:
    - voyage-3 (default, 1024 dims)
    - voyage-3-lite (512 dims, faster)
    - voyage-code-3 (optimised for code)
    - voyage-finance-2 (optimised for financial text)
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        api_key: str | None = None,
        dimensions: int = _DEFAULT_DIMENSIONS,
    ) -> None:
        super().__init__(model=model)
        self._api_key = api_key or os.environ.get("VOYAGE_API_KEY")
        self._dimensions = dimensions
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import voyageai  # type: ignore[import]
                self._client = voyageai.Client(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "voyageai package required for Voyage embeddings. "
                    "Install with: pip install voyageai"
                )
        return self._client

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts."""
        import asyncio

        client = self._get_client()
        loop = asyncio.get_event_loop()

        def _sync_embed():
            response = client.embed(texts, model=self.model)
            return [emb for emb in response.embeddings]

        return await loop.run_in_executor(None, _sync_embed)

    def get_dimensions(self) -> int:
        return self._dimensions

    def get_model_name(self) -> str:
        return self.model


__all__ = ["VoyageEmbeddingProvider"]
