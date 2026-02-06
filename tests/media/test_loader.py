"""
Tests for media loader

Matches TypeScript src/web/media.ts
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from openclaw.media.loader import MediaLoader, load_media
from openclaw.media.mime import MediaKind


class TestDataUrlLoading:
    """Tests for data URL loading."""
    
    @pytest.mark.asyncio
    async def test_valid_data_url(self):
        # 1x1 red pixel PNG
        data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        
        loader = MediaLoader()
        result = await loader.load(data_url)
        
        assert result.kind == MediaKind.IMAGE
        assert result.content_type == "image/png"
        assert len(result.buffer) > 0
    
    @pytest.mark.asyncio
    async def test_invalid_data_url(self):
        loader = MediaLoader()
        
        with pytest.raises(ValueError, match="Invalid data URL"):
            await loader.load("data:invalid")


class TestFileLoading:
    """Tests for file loading."""
    
    @pytest.mark.asyncio
    async def test_load_existing_file(self, tmp_path):
        # Create test image
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"PNG_FAKE_DATA")
        
        loader = MediaLoader()
        result = await loader.load(str(test_file))
        
        assert result.buffer == b"PNG_FAKE_DATA"
        assert result.file_name == "test.png"
    
    @pytest.mark.asyncio
    async def test_file_not_found(self):
        loader = MediaLoader()
        
        with pytest.raises(FileNotFoundError):
            await loader.load("/nonexistent/file.png")
    
    @pytest.mark.asyncio
    async def test_file_url_prefix(self, tmp_path):
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"DATA")
        
        loader = MediaLoader()
        result = await loader.load(f"file://{test_file}")
        
        assert result.buffer == b"DATA"


class TestSizeLimit:
    """Tests for size limits."""
    
    @pytest.mark.asyncio
    async def test_exceeds_limit(self, tmp_path):
        test_file = tmp_path / "large.png"
        test_file.write_bytes(b"X" * 10000)
        
        loader = MediaLoader(max_bytes=1000)
        
        with pytest.raises(ValueError, match="exceeds size limit"):
            await loader.load(str(test_file))


class TestSandboxedAccess:
    """Tests for sandboxed access."""
    
    @pytest.mark.asyncio
    async def test_inside_workspace(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        test_file = workspace / "image.png"
        test_file.write_bytes(b"DATA")
        
        loader = MediaLoader(workspace_root=workspace)
        result = await loader.load(str(test_file))
        
        assert result.buffer == b"DATA"
    
    @pytest.mark.asyncio
    async def test_outside_workspace_fails(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        outside_file = tmp_path / "outside.png"
        outside_file.write_bytes(b"DATA")
        
        loader = MediaLoader(workspace_root=workspace)
        
        with pytest.raises(ValueError, match="Path outside workspace"):
            await loader.load(str(outside_file))
    
    @pytest.mark.asyncio
    async def test_media_inbound_fallback(self, tmp_path):
        """Test media/inbound fallback (matches TS resolveSandboxedImagePath)."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Create media/inbound directory
        media_dir = workspace / "media" / "inbound"
        media_dir.mkdir(parents=True)
        
        test_file = media_dir / "photo.png"
        test_file.write_bytes(b"DATA")
        
        loader = MediaLoader(workspace_root=workspace)
        
        # Try to load with just filename (should fallback to media/inbound)
        result = await loader.load("photo.png")
        
        assert result.buffer == b"DATA"


class TestConvenienceFunction:
    """Tests for load_media convenience function."""
    
    @pytest.mark.asyncio
    async def test_load_media(self, tmp_path):
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"JPEG_DATA")
        
        result = await load_media(str(test_file))
        
        assert result.buffer == b"JPEG_DATA"
        assert result.kind == MediaKind.IMAGE
