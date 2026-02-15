"""Edge case tests for tool system"""
import asyncio
import os
import tempfile
import pytest

from openclaw.agents.tools import (
    create_bash_tool,
    create_read_tool,
    create_write_tool,
    create_edit_tool,
)
from openclaw.agents.types import AgentToolResult


@pytest.mark.asyncio
async def test_empty_file():
    """Test reading an empty file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Write empty file
        await write_tool.execute(
            tool_call_id="write-empty",
            params={"path": "empty.txt", "content": ""},
            signal=None,
            on_update=None,
        )
        
        # Read empty file
        result = await read_tool.execute(
            tool_call_id="read-empty",
            params={"path": "empty.txt"},
            signal=None,
            on_update=None,
        )
        
        assert isinstance(result, AgentToolResult)


@pytest.mark.asyncio
async def test_single_line_file():
    """Test reading a single line file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Write single line
        await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "single.txt", "content": "single line"},
            signal=None,
            on_update=None,
        )
        
        # Read it
        result = await read_tool.execute(
            tool_call_id="read-1",
            params={"path": "single.txt"},
            signal=None,
            on_update=None,
        )
        
        assert "single line" in result.content[0].text


@pytest.mark.asyncio
async def test_file_with_no_newline_at_end():
    """Test file that doesn't end with newline"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        edit_tool = create_edit_tool(tmpdir)
        
        # Write file without trailing newline
        content = "line1\nline2"
        await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "no-newline.txt", "content": content},
            signal=None,
            on_update=None,
        )
        
        # Read it
        result = await read_tool.execute(
            tool_call_id="read-1",
            params={"path": "no-newline.txt"},
            signal=None,
            on_update=None,
        )
        
        assert "line1" in result.content[0].text
        assert "line2" in result.content[0].text
        
        # Edit it
        result = await edit_tool.execute(
            tool_call_id="edit-1",
            params={
                "path": "no-newline.txt",
                "oldText": "line2",
                "newText": "line2 modified",
            },
            signal=None,
            on_update=None,
        )
        
        assert isinstance(result, AgentToolResult)


@pytest.mark.asyncio
async def test_bash_empty_output():
    """Test bash command with no output"""
    bash_tool = create_bash_tool("/tmp")
    
    result = await bash_tool.execute(
        tool_call_id="bash-empty",
        params={"command": "true"},  # Command with no output
        signal=None,
        on_update=None,
    )
    
    assert isinstance(result, AgentToolResult)


@pytest.mark.asyncio
async def test_bash_stderr_output():
    """Test bash command with stderr output"""
    bash_tool = create_bash_tool("/tmp")
    
    # Command that writes to stderr (should be combined with stdout)
    result = await bash_tool.execute(
        tool_call_id="bash-stderr",
        params={"command": "echo 'error message' >&2"},
        signal=None,
        on_update=None,
    )
    
    assert isinstance(result, AgentToolResult)
    # stderr is combined with stdout in our implementation
    assert "error message" in result.content[0].text


@pytest.mark.asyncio
async def test_edit_with_whitespace_variations():
    """Test edit with different whitespace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        edit_tool = create_edit_tool(tmpdir)
        
        # Write file with trailing spaces
        content = "line1  \nline2\t\nline3   "
        await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "whitespace.txt", "content": content},
            signal=None,
            on_update=None,
        )
        
        # Edit should handle fuzzy whitespace matching
        result = await edit_tool.execute(
            tool_call_id="edit-1",
            params={
                "path": "whitespace.txt",
                "oldText": "line2",  # Without tab
                "newText": "line2 modified",
            },
            signal=None,
            on_update=None,
        )
        
        assert isinstance(result, AgentToolResult)


@pytest.mark.asyncio
async def test_special_characters_in_paths():
    """Test files with special characters in names"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # File with spaces
        await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "file with spaces.txt", "content": "test"},
            signal=None,
            on_update=None,
        )
        
        result = await read_tool.execute(
            tool_call_id="read-1",
            params={"path": "file with spaces.txt"},
            signal=None,
            on_update=None,
        )
        
        assert "test" in result.content[0].text


@pytest.mark.asyncio
async def test_nested_directory_creation():
    """Test creating files in nested directories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Write to nested path (should auto-create directories)
        await write_tool.execute(
            tool_call_id="write-nested",
            params={"path": "a/b/c/file.txt", "content": "nested"},
            signal=None,
            on_update=None,
        )
        
        # Verify it was created
        nested_file = os.path.join(tmpdir, "a", "b", "c", "file.txt")
        assert os.path.exists(nested_file)
        
        # Read it back
        result = await read_tool.execute(
            tool_call_id="read-nested",
            params={"path": "a/b/c/file.txt"},
            signal=None,
            on_update=None,
        )
        
        assert "nested" in result.content[0].text


@pytest.mark.asyncio
async def test_read_offset_beyond_file_end():
    """Test read with offset beyond file end"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Write small file
        await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "small.txt", "content": "line1\nline2"},
            signal=None,
            on_update=None,
        )
        
        # Try to read beyond end
        with pytest.raises(ValueError) as exc_info:
            await read_tool.execute(
                tool_call_id="read-1",
                params={"path": "small.txt", "offset": 100},
                signal=None,
                on_update=None,
            )
        
        assert "beyond end" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_bash_with_pipes():
    """Test bash command with pipes"""
    bash_tool = create_bash_tool("/tmp")
    
    result = await bash_tool.execute(
        tool_call_id="bash-pipe",
        params={"command": "echo 'hello world' | wc -w"},
        signal=None,
        on_update=None,
    )
    
    assert isinstance(result, AgentToolResult)
    assert "2" in result.content[0].text


@pytest.mark.asyncio
async def test_bash_with_environment_variables():
    """Test bash command using environment variables"""
    bash_tool = create_bash_tool("/tmp")
    
    result = await bash_tool.execute(
        tool_call_id="bash-env",
        params={"command": "echo $USER"},
        signal=None,
        on_update=None,
    )
    
    assert isinstance(result, AgentToolResult)
    # Should output something (the username)
    assert len(result.content[0].text.strip()) > 0


@pytest.mark.asyncio
async def test_edit_with_no_changes():
    """Test edit where old and new text are the same"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        edit_tool = create_edit_tool(tmpdir)
        
        content = "hello world"
        await write_tool.execute(
            tool_call_id="write-1",
            params={"path": "test.txt", "content": content},
            signal=None,
            on_update=None,
        )
        
        # Try to "edit" with same text
        with pytest.raises(ValueError) as exc_info:
            await edit_tool.execute(
                tool_call_id="edit-1",
                params={
                    "path": "test.txt",
                    "oldText": "hello",
                    "newText": "hello",
                },
                signal=None,
                on_update=None,
            )
        
        assert "no changes" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_very_long_single_line():
    """Test file with a very long single line"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        read_tool = create_read_tool(tmpdir)
        
        # Create a very long single line (>50KB)
        long_line = "x" * 60000
        await write_tool.execute(
            tool_call_id="write-long",
            params={"path": "long-line.txt", "content": long_line},
            signal=None,
            on_update=None,
        )
        
        # Read it (should handle truncation)
        result = await read_tool.execute(
            tool_call_id="read-long",
            params={"path": "long-line.txt"},
            signal=None,
            on_update=None,
        )
        
        # Should indicate first line exceeds limit
        assert "exceeds" in result.content[0].text.lower() or "bash" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_line_ending_preservation():
    """Test that line endings are preserved"""
    with tempfile.TemporaryDirectory() as tmpdir:
        write_tool = create_write_tool(tmpdir)
        edit_tool = create_edit_tool(tmpdir)
        
        # Write file with CRLF line endings
        content_crlf = "line1\r\nline2\r\nline3"
        await write_tool.execute(
            tool_call_id="write-crlf",
            params={"path": "crlf.txt", "content": content_crlf},
            signal=None,
            on_update=None,
        )
        
        # Edit it
        await edit_tool.execute(
            tool_call_id="edit-crlf",
            params={
                "path": "crlf.txt",
                "oldText": "line2",
                "newText": "line2 modified",
            },
            signal=None,
            on_update=None,
        )
        
        # Read back and verify CRLF is preserved
        file_path = os.path.join(tmpdir, "crlf.txt")
        with open(file_path, 'rb') as f:
            raw_content = f.read()
        
        # Should still contain CRLF
        assert b'\r\n' in raw_content
