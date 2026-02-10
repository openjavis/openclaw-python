"""Base embedding provider interface"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class EmbeddingBatch:
    """Batch of embeddings"""
    
    texts: List[str]
    embeddings: List[List[float]]
    model: str
    dimensions: int


class EmbeddingProvider(ABC):
    """
    Base class for embedding providers
    
    Providers generate vector embeddings for text chunks.
    """
    
    def __init__(self, model: str = "default"):
        """
        Initialize embedding provider
        
        Args:
            model: Model name
        """
        self.model = model
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Embed single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_batch(
        self,
        texts: List[str],
        use_batch_api: bool = False
    ) -> EmbeddingBatch:
        """
        Embed batch of texts
        
        Args:
            texts: Texts to embed
            use_batch_api: Use provider's batch API if available
            
        Returns:
            Batch of embeddings
        """
        pass
    
    @abstractmethod
    def get_dimensions(self) -> int:
        """Get embedding dimensions for this model"""
        pass
