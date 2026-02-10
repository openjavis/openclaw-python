"""Gemini embedding provider"""
from __future__ import annotations

import logging
from typing import List

from .base import EmbeddingProvider, EmbeddingBatch

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Gemini embedding provider
    
    Supports:
    - text-embedding-004 (768 dims)
    - embedding-001 (768 dims, legacy)
    """
    
    def __init__(self, model: str = "text-embedding-004", api_key: str | None = None):
        """
        Initialize Gemini provider
        
        Args:
            model: Model name
            api_key: Optional API key
        """
        super().__init__(model)
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        """Get or create Gemini client"""
        if self._client is None:
            try:
                import google.generativeai as genai
            except ImportError:
                raise RuntimeError(
                    "google-generativeai package not installed. "
                    "Install with: pip install google-generativeai"
                )
            
            if self.api_key:
                genai.configure(api_key=self.api_key)
            
            self._client = genai
        
        return self._client
    
    async def embed_text(self, text: str) -> List[float]:
        """Embed single text"""
        client = self._get_client()
        
        result = client.embed_content(
            model=f"models/{self.model}",
            content=text,
            task_type="retrieval_document",
        )
        
        return result["embedding"]
    
    async def embed_batch(
        self,
        texts: List[str],
        use_batch_api: bool = False
    ) -> EmbeddingBatch:
        """Embed batch of texts"""
        client = self._get_client()
        
        # Gemini supports batch embedding
        result = client.embed_content(
            model=f"models/{self.model}",
            content=texts,
            task_type="retrieval_document",
        )
        
        embeddings = result["embedding"]
        
        return EmbeddingBatch(
            texts=texts,
            embeddings=embeddings,
            model=self.model,
            dimensions=self.get_dimensions(),
        )
    
    def get_dimensions(self) -> int:
        """Get embedding dimensions"""
        # Gemini embeddings are 768-dimensional
        return 768
