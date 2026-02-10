"""OpenAI embedding provider"""
from __future__ import annotations

import logging
from typing import List

from .base import EmbeddingProvider, EmbeddingBatch

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider
    
    Supports:
    - text-embedding-3-small (1536 dims)
    - text-embedding-3-large (3072 dims)
    - text-embedding-ada-002 (1536 dims, legacy)
    - Batch API support
    """
    
    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        """
        Initialize OpenAI provider
        
        Args:
            model: Model name
            api_key: Optional API key (uses env var if not provided)
        """
        super().__init__(model)
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        """Get or create OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise RuntimeError("openai package not installed. Install with: pip install openai")
            
            self._client = AsyncOpenAI(api_key=self.api_key)
        
        return self._client
    
    async def embed_text(self, text: str) -> List[float]:
        """Embed single text"""
        client = self._get_client()
        
        response = await client.embeddings.create(
            model=self.model,
            input=text,
        )
        
        return response.data[0].embedding
    
    async def embed_batch(
        self,
        texts: List[str],
        use_batch_api: bool = False
    ) -> EmbeddingBatch:
        """
        Embed batch of texts
        
        Args:
            texts: Texts to embed
            use_batch_api: Use Batch API (for large batches, async processing)
            
        Returns:
            Batch of embeddings
        """
        if use_batch_api:
            # TODO: Implement Batch API support
            # This requires creating batch file, uploading, polling for completion
            logger.warning("Batch API not yet implemented, using regular API")
        
        client = self._get_client()
        
        # Regular batch embedding
        response = await client.embeddings.create(
            model=self.model,
            input=texts,
        )
        
        # Extract embeddings in order
        embeddings = [item.embedding for item in response.data]
        
        return EmbeddingBatch(
            texts=texts,
            embeddings=embeddings,
            model=self.model,
            dimensions=self.get_dimensions(),
        )
    
    def get_dimensions(self) -> int:
        """Get embedding dimensions"""
        dimensions_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        
        return dimensions_map.get(self.model, 1536)
