"""Tools tests"""

import tempfile
from pathlib import Path

import pytest

from openclaw.agents.tools.base import AgentTool, ToolResult
from openclaw.agents.tools.file_ops import ReadFileTool, WriteFileTool
from openclaw.agents.tools.registry import get_tool_registry


def test_tool_registry():
    """Test tool registry"""
    registry = get_tool_registry()

    tools = registry.list_tools()
    assert len(tools) > 0

    # Check for core tools
    assert registry.get("read_file") is not None
    assert registry.get("write_file") is not None
    assert registry.get("bash") is not None


@pytest.mark.asyncio
async def test_read_file_tool():
    """Test read file tool"""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Test content")
        temp_path = f.name

    try:
        tool = ReadFileTool()
        result = await tool.execute({"path": temp_path})

        assert result.success
        assert result.content == "Test content"
    finally:
        Path(temp_path).unlink()


@pytest.mark.asyncio
async def test_write_file_tool():
    """Test write file tool"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"

        tool = WriteFileTool()
        result = await tool.execute({"path": str(file_path), "content": "New content"})

        assert result.success
        assert file_path.exists()
        assert file_path.read_text() == "New content"


@pytest.mark.asyncio
async def test_tool_profile_filtering():
    """Test tool profile filtering"""
    registry = get_tool_registry()

    minimal_tools = registry.get_tools_by_profile("minimal")
    full_tools = registry.get_tools_by_profile("full")

    assert len(minimal_tools) < len(full_tools)
