"""
Tests for image operations

Matches TypeScript src/media/image-ops.ts
"""
from __future__ import annotations

import io

import pytest

from openclaw.media.image_ops import ImageProcessor


@pytest.fixture
def sample_image_buffer():
    """Create a small sample image buffer."""
    try:
        from PIL import Image
        
        # Create 100x100 red image
        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except ImportError:
        pytest.skip("Pillow not available")


@pytest.fixture
def sample_image_with_alpha():
    """Create a sample image with alpha channel."""
    try:
        from PIL import Image
        
        # Create 100x100 image with transparency
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except ImportError:
        pytest.skip("Pillow not available")


class TestImageMetadata:
    """Tests for image metadata extraction."""
    
    @pytest.mark.asyncio
    async def test_get_metadata(self, sample_image_buffer):
        metadata = await ImageProcessor.get_image_metadata(sample_image_buffer)
        
        assert metadata.width == 100
        assert metadata.height == 100
        assert metadata.format == "PNG"
    
    @pytest.mark.asyncio
    async def test_has_alpha_channel(self, sample_image_buffer, sample_image_with_alpha):
        # No alpha
        has_alpha = await ImageProcessor.has_alpha_channel(sample_image_buffer)
        assert not has_alpha
        
        # Has alpha
        has_alpha = await ImageProcessor.has_alpha_channel(sample_image_with_alpha)
        assert has_alpha


class TestImageResize:
    """Tests for image resizing."""
    
    @pytest.mark.asyncio
    async def test_resize_to_jpeg(self, sample_image_buffer):
        resized = await ImageProcessor.resize_to_jpeg(
            sample_image_buffer,
            max_side=50,
            quality=85
        )
        
        # Check it's smaller
        assert len(resized) < len(sample_image_buffer)
        
        # Verify it's a valid image
        metadata = await ImageProcessor.get_image_metadata(resized)
        assert metadata.width <= 50
        assert metadata.height <= 50
    
    @pytest.mark.asyncio
    async def test_resize_maintains_aspect(self, sample_image_buffer):
        # Create 200x100 image
        from PIL import Image
        img = Image.new("RGB", (200, 100), color="blue")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        
        resized = await ImageProcessor.resize_to_jpeg(buffer.getvalue(), max_side=100)
        
        metadata = await ImageProcessor.get_image_metadata(resized)
        # Should be 100x50 (maintaining 2:1 aspect ratio)
        assert metadata.width == 100
        assert metadata.height == 50


class TestImageOptimization:
    """Tests for image optimization."""
    
    @pytest.mark.asyncio
    async def test_optimize_to_png(self, sample_image_with_alpha):
        optimized = await ImageProcessor.optimize_to_png(
            sample_image_with_alpha,
            max_side=50,
            compression_level=9
        )
        
        # Should be smaller
        assert len(optimized) < len(sample_image_with_alpha)
        
        # Should still have alpha
        has_alpha = await ImageProcessor.has_alpha_channel(optimized)
        assert has_alpha
    
    @pytest.mark.asyncio
    async def test_optimize_image_under_limit(self, sample_image_buffer):
        """If already under limit, return as-is."""
        optimized = await ImageProcessor.optimize_image(
            sample_image_buffer,
            max_bytes=len(sample_image_buffer) + 1000,
            preserve_alpha=True
        )
        
        assert len(optimized.buffer) <= len(sample_image_buffer) + 1000
    
    @pytest.mark.asyncio
    async def test_optimize_image_reduces_size(self, sample_image_buffer):
        """Optimize to fit within limit."""
        # Set aggressive limit
        optimized = await ImageProcessor.optimize_image(
            sample_image_buffer,
            max_bytes=500,  # Very small
            preserve_alpha=False
        )
        
        assert len(optimized.buffer) <= 500
        assert optimized.format in ("jpeg", "png")


class TestPillowAvailability:
    """Tests for Pillow availability check."""
    
    def test_has_pillow(self):
        # This test will pass if Pillow is installed
        has_it = ImageProcessor.has_pillow()
        assert isinstance(has_it, bool)
