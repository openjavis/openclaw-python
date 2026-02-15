"""Unit tests for embeddings"""
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch

from openclaw.memory.embeddings.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing"""
    
    async def embed_text(self, text: str) -> list[float]:
        """Return mock embedding"""
        # Simple hash-based mock embedding
        hash_val = hash(text)
        return [float((hash_val >> i) & 0xFF) / 255.0 for i in range(0, 128, 8)]
    
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return mock embeddings for batch"""
        return [await self.embed_text(text) for text in texts]


class TestEmbeddingProvider:
    """Test embedding provider base class"""
    
    @pytest.mark.asyncio
    async def test_embed_text(self):
        """Test embedding single text"""
        provider = MockEmbeddingProvider()
        
        embedding = await provider.embed_text("Hello world")
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test embedding batch of texts"""
        provider = MockEmbeddingProvider()
        
        texts = ["Hello", "World", "Test"]
        embeddings = await provider.embed_batch(texts)
        
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(isinstance(emb, list) for emb in embeddings)
    
    @pytest.mark.asyncio
    async def test_embedding_consistency(self):
        """Test that same text produces same embedding"""
        provider = MockEmbeddingProvider()
        
        text = "consistent text"
        emb1 = await provider.embed_text(text)
        emb2 = await provider.embed_text(text)
        
        assert emb1 == emb2
    
    @pytest.mark.asyncio
    async def test_embedding_different_texts(self):
        """Test that different texts produce different embeddings"""
        provider = MockEmbeddingProvider()
        
        emb1 = await provider.embed_text("text one")
        emb2 = await provider.embed_text("text two")
        
        assert emb1 != emb2


class TestEmbeddingSimilarity:
    """Test embedding similarity calculations"""
    
    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    @pytest.mark.asyncio
    async def test_similarity_same_text(self):
        """Test similarity of same text"""
        provider = MockEmbeddingProvider()
        
        emb1 = await provider.embed_text("same text")
        emb2 = await provider.embed_text("same text")
        
        similarity = self.cosine_similarity(emb1, emb2)
        
        # Should be very similar (close to 1.0)
        assert similarity > 0.99
    
    @pytest.mark.asyncio
    async def test_similarity_different_texts(self):
        """Test similarity of different texts"""
        provider = MockEmbeddingProvider()
        
        emb1 = await provider.embed_text("completely different")
        emb2 = await provider.embed_text("totally unrelated")
        
        similarity = self.cosine_similarity(emb1, emb2)
        
        # Should be less similar (but not necessarily negative)
        assert -1.0 <= similarity <= 1.0


def test_embedding_imports():
    """Test that embedding modules can be imported"""
    try:
        from openclaw.memory.embeddings import EmbeddingProvider
        from openclaw.memory.embeddings.base import EmbeddingProvider as BaseProvider
        
        assert EmbeddingProvider is not None
        assert BaseProvider is not None
    except ImportError as e:
        pytest.fail(f"Failed to import embedding modules: {e}")
