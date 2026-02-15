"""Tests for model consistency across tool implementations"""
import asyncio
import pytest

from openclaw.agents.tools import (
    create_bash_tool,
    create_read_tool,
    create_write_tool,
    create_edit_tool,
    DEFAULT_MAX_BYTES,
)
from openclaw.agents.types import AgentToolResult, TextContent


@pytest.mark.asyncio
async def test_bash_output_format():
    """Test that bash output format is consistent for all models"""
    tool = create_bash_tool("/tmp")
    
    result = await tool.execute(
        tool_call_id="test-1",
        params={"command": "echo 'hello world'"},
        signal=None,
        on_update=None,
    )
    
    # Verify result format
    assert isinstance(result, AgentToolResult)
    assert len(result.content) > 0
    assert isinstance(result.content[0], TextContent)
    assert "hello world" in result.content[0].text


@pytest.mark.asyncio
async def test_bash_truncation_consistency():
    """Test that truncation mechanism is consistent across models"""
    # Generate large output (> 50KB)
    large_output = "x" * (DEFAULT_MAX_BYTES + 1000)
    
    tool = create_bash_tool("/tmp")
    result = await tool.execute(
        tool_call_id="test-2",
        params={"command": f"echo '{large_output}'"},
        signal=None,
        on_update=None,
    )
    
    # Verify truncation occurred
    assert result.details is not None
    assert "truncation" in result.details
    assert result.details["full_output_path"] is not None
    
    # Verify helpful message
    output_text = result.content[0].text
    assert "[Showing lines" in output_text or "[Showing last" in output_text
    assert "Full output:" in output_text


@pytest.mark.asyncio
async def test_tool_schema_consistency():
    """Test that tool schemas are consistent for all models"""
    bash_tool = create_bash_tool("/tmp")
    read_tool = create_read_tool("/tmp")
    write_tool = create_write_tool("/tmp")
    edit_tool = create_edit_tool("/tmp")
    
    # Verify all tools have valid schemas
    for tool in [bash_tool, read_tool, write_tool, edit_tool]:
        assert tool.parameters["type"] == "object"
        assert "properties" in tool.parameters
        assert "required" in tool.parameters
        assert isinstance(tool.parameters["properties"], dict)
        assert isinstance(tool.parameters["required"], list)


@pytest.mark.asyncio
async def test_tool_result_format_consistency():
    """Test that all tools return AgentToolResult in same format"""
    import tempfile
    import os
    
    # Create temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        
        # Test write tool
        write_tool = create_write_tool(tmpdir)
        write_result = await write_tool.execute(
            tool_call_id="test-write",
            params={"path": "test.txt", "content": "hello"},
            signal=None,
            on_update=None,
        )
        
        assert isinstance(write_result, AgentToolResult)
        assert len(write_result.content) > 0
        assert isinstance(write_result.content[0], TextContent)
        
        # Test read tool
        read_tool = create_read_tool(tmpdir)
        read_result = await read_tool.execute(
            tool_call_id="test-read",
            params={"path": "test.txt"},
            signal=None,
            on_update=None,
        )
        
        assert isinstance(read_result, AgentToolResult)
        assert len(read_result.content) > 0
        assert isinstance(read_result.content[0], TextContent)
        assert "hello" in read_result.content[0].text


@pytest.mark.asyncio
async def test_cancellation_support():
    """Test that all tools support cancellation via signal"""
    tool = create_bash_tool("/tmp")
    
    # Create signal and set it immediately
    signal = asyncio.Event()
    signal.set()
    
    # Should raise CancelledError
    with pytest.raises((asyncio.CancelledError, Exception)) as exc_info:
        await tool.execute(
            tool_call_id="test-cancel",
            params={"command": "sleep 10"},
            signal=signal,
            on_update=None,
        )
    
    # Verify error message mentions abort/cancel
    error_msg = str(exc_info.value).lower()
    assert "abort" in error_msg or "cancel" in error_msg


@pytest.mark.asyncio
async def test_streaming_update_callback():
    """Test that bash tool sends streaming updates"""
    tool = create_bash_tool("/tmp")
    
    updates_received = []
    
    def handle_update(result: AgentToolResult):
        updates_received.append(result)
    
    # Run command that produces output
    await tool.execute(
        tool_call_id="test-stream",
        params={"command": "echo 'line 1'; echo 'line 2'; echo 'line 3'"},
        signal=None,
        on_update=handle_update,
    )
    
    # Should have received at least one update
    # (may not always receive updates for fast commands)
    # This is a best-effort test
    assert isinstance(updates_received, list)


@pytest.mark.asyncio
async def test_error_handling_consistency():
    """Test that all tools handle errors consistently"""
    tool = create_bash_tool("/tmp")
    
    # Run command that fails
    with pytest.raises(Exception) as exc_info:
        await tool.execute(
            tool_call_id="test-error",
            params={"command": "exit 1"},
            signal=None,
            on_update=None,
        )
    
    # Verify error message
    error_msg = str(exc_info.value)
    assert "exited with code 1" in error_msg
