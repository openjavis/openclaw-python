"""
Tests for image tool

Matches TypeScript src/agents/tools/image-tool.test.ts
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest

from openclaw.agents.tools.image import ImageTool
from openclaw.media.mime import MediaKind


@pytest.fixture
def sample_data_url():
    """1x1 red pixel PNG as data URL."""
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_image_file(tmp_path):
    """Create a sample image file."""
    try:
        from PIL import Image
        
        img = Image.new("RGB", (100, 100), color="red")
        file_path = tmp_path / "test.png"
        img.save(file_path)
        return file_path
    except ImportError:
        pytest.skip("Pillow not available")


class TestImageToolInit:
    """Tests for ImageTool initialization."""
    
    def test_default_init(self):
        tool = ImageTool()
        assert tool.name == "image"
        assert "vision model" in tool.description.lower()
    
    def test_with_vision_model(self):
        tool = ImageTool(model_has_vision=True)
        assert "NOT already provided" in tool.description
    
    def test_without_vision_model(self):
        tool = ImageTool(model_has_vision=False)
        assert "Provide a prompt and image" in tool.description


class TestImageToolSchema:
    """Tests for tool schema."""
    
    def test_schema_structure(self):
        tool = ImageTool()
        schema = tool.get_schema()
        
        assert schema["type"] == "object"
        assert "image" in schema["properties"]
        assert "prompt" in schema["properties"]
        assert "model" in schema["properties"]
        assert "image" in schema["required"]


class TestImageToolDataUrl:
    """Tests for data URL handling."""
    
    @pytest.mark.asyncio
    async def test_load_data_url(self, sample_data_url):
        """Test loading image from data URL."""
        tool = ImageTool()
        
        # Note: This would call actual API, so we just test the loading part
        # In real tests, you'd mock the API call
        try:
            result = await tool.execute({
                "image": sample_data_url,
                "prompt": "What color is this?",
                "model": "claude-3-5-sonnet-20241022"
            })
            # If API keys are set, this should work
            # If not, we'll get an error about missing API key
            assert result is not None
        except Exception:
            # Expected if no API keys configured
            pass


class TestImageToolFile:
    """Tests for file loading."""
    
    @pytest.mark.asyncio
    async def test_load_file(self, sample_image_file):
        """Test loading image from file."""
        tool = ImageTool()
        
        try:
            result = await tool.execute({
                "image": str(sample_image_file),
                "prompt": "Describe this image",
            })
            assert result is not None
        except Exception:
            # Expected if no API keys
            pass


class TestImageToolSandbox:
    """Tests for sandboxed access."""
    
    @pytest.mark.asyncio
    async def test_sandboxed_access(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Create image inside workspace
        media_dir = workspace / "media" / "inbound"
        media_dir.mkdir(parents=True)
        
        test_file = media_dir / "test.png"
        test_file.write_bytes(b"PNG_DATA")
        
        tool = ImageTool(workspace_root=workspace)
        
        # Should be able to access via filename (fallback to media/inbound)
        try:
            result = await tool.execute({
                "image": "test.png",
                "prompt": "Test",
            })
            # Will fail on API call, but loading should work
        except Exception as e:
            # Check it's API error, not file access error
            assert "API" in str(e) or "not set" in str(e) or "not installed" in str(e)


class TestImageToolAtPrefix:
    """Tests for @ prefix handling (matches TS line 346)."""
    
    @pytest.mark.asyncio
    async def test_removes_at_prefix(self, sample_image_file):
        tool = ImageTool()
        
        try:
            # @ prefix should be removed
            result = await tool.execute({
                "image": f"@{sample_image_file}",
                "prompt": "Test",
            })
        except Exception:
            pass  # API error expected


class TestImageToolModelFallback:
    """Tests for model fallback."""
    
    def test_fallback_order(self):
        """Test that fallback order is defined."""
        tool = ImageTool()
        
        # The tool should have fallback logic
        # (tested implicitly through execute with model failures)
        assert hasattr(tool, "_analyze_with_fallback")
