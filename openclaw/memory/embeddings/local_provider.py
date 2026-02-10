"""Local embedding provider using llama.cpp or sentence-transformers"""
from __future__ import annotations

import logging
from typing import List

from .base import EmbeddingProvider, EmbeddingBatch

logger = logging.getLogger(__name__)


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider
    
    Supports:
    - sentence-transformers models
    - llama.cpp embeddings
    """
    
    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        backend: str = "sentence-transformers"
    ):
        """
        Initialize local provider
        
        Args:
            model: Model name or path
            backend: Backend to use ("sentence-transformers" or "llama-cpp")
        """
        super().__init__(model)
        self.backend = backend
        self._model_instance = None
    
    def _load_model(self):
        """Load embedding model"""
        if self._model_instance is not None:
            return self._model_instance
        
        if self.backend == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            
            logger.info(f"Loading sentence-transformers model: {self.model}")
            self._model_instance = SentenceTransformer(self.model)
            
        elif self.backend == "llama-cpp":
            # TODO: Implement llama.cpp backend
            raise NotImplementedError("llama-cpp backend not yet implemented")
        
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
        
        return self._model_instance
    
    async def embed_text(self, text: str) -> List[float]:
        """Embed single text"""
        model = self._load_model()
        
        # sentence-transformers returns numpy array
        embedding = model.encode(text, convert_to_numpy=True)
        
        return embedding.tolist()
    
    async def embed_batch(
        self,
        texts: List[str],
        use_batch_api: bool = False
    ) -> EmbeddingBatch:
        """Embed batch of texts"""
        model = self._load_model()
        
        # Batch encode
        embeddings_array = model.encode(texts, convert_to_numpy=True)
        
        # Convert to list
        embeddings = [emb.tolist() for emb in embeddings_array]
        
        return EmbeddingBatch(
            texts=texts,
            embeddings=embeddings,
            model=self.model,
            dimensions=self.get_dimensions(),
        )
    
    def get_dimensions(self) -> int:
        """Get embedding dimensions"""
        # Load model to get dimensions
        model = self._load_model()
        
        if self.backend == "sentence-transformers":
            return model.get_sentence_embedding_dimension()
        
        return 384  # Default for many models
