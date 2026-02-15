"""Integration tests for tool system"""
import asyncio
import os
import tempfile
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
async def test_write_read_workflow():
    """Test writing a file and then reading it back"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Write file
        content = "Hello, World!\nThis is a test file."
        write_result = await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "test.txt", "content": content},
            signal=None,
            on_update=None,
        )
        
        assert isinstance(write_result, AgentToolResult)
        assert "Successfully wrote" in write_result.content[0].text
        
        # Read file back
        read_result = await read_tool.execute(
            tool_call_id="read-1",
            params={"path": "test.txt"},
            signal=None,
            on_update=None,
        )
        
        assert isinstance(read_result, AgentToolResult)
        assert content in read_result.content[0].text


@pytest.mark.asyncio
async def test_write_edit_read_workflow():
    """Test writing, editing, and reading a file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        edit_tool = create_edit_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Write initial file
        initial_content = "def hello():\n    print('Hello')"
        await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "code.py", "content": initial_content},
            signal=None,
            on_update=None,
        )
        
        # Edit file
        edit_result = await edit_tool.execute(
            tool_call_id="edit-1",
            params={
                "path": "code.py",
                "oldText": "print('Hello')",
                "newText": "print('Hello, World!')",
            },
            signal=None,
            on_update=None,
        )
        
        assert isinstance(edit_result, AgentToolResult)
        assert "Successfully replaced" in edit_result.content[0].text
        assert edit_result.details is not None
        assert "diff" in edit_result.details
        
        # Read edited file
        read_result = await read_tool.execute(
            tool_call_id="read-1",
            params={"path": "code.py"},
            signal=None,
            on_update=None,
        )
        
        assert "Hello, World!" in read_result.content[0].text
        assert "print('Hello')" not in read_result.content[0].text


@pytest.mark.asyncio
async def test_bash_with_file_operations():
    """Test bash tool with file operations"""
    with tempfile.TemporaryDirectory() as tmpdir:
        bash_tool = create_bash_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Create file using bash
        result = await bash_tool.execute(
            tool_call_id="bash-1",
            params={"command": "echo 'test content' > test.txt"},
            signal=None,
            on_update=None,
        )
        
        assert isinstance(result, AgentToolResult)
        
        # Verify file was created
        test_file = os.path.join(tmpdir, "test.txt")
        assert os.path.exists(test_file)
        
        # Read file
        read_result = await read_tool.execute(
            tool_call_id="read-1",
            params={"path": "test.txt"},
            signal=None,
            on_update=None,
        )
        
        assert "test content" in read_result.content[0].text
