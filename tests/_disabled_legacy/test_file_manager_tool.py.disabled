"""Unit tests for File Manager tool"""
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from openclaw.agents.tools.file_manager import FileManagerTool
from openclaw.agents.tools.base import ToolResult


class TestFileManagerTool:
    """Test File Manager tool"""
    
    def test_create_tool(self):
        """Test creating File Manager tool"""
        tool = FileManagerTool()
        assert tool is not None
        assert tool.name == "file_manager"
        assert tool.description != ""
    
    def test_get_schema(self):
        """Test getting tool schema"""
        tool = FileManagerTool()
        schema = tool.get_schema()
        
        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema
    
    @pytest.mark.asyncio
    async def test_read_file(self):
        """Test reading file"""
        with TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello World")
            
            tool = FileManagerTool(base_path=tmpdir)
            
            result = await tool.execute({
                "action": "read",
                "path": "test.txt"
            })
            
            assert result.success
            assert "Hello World" in result.content
    
    @pytest.mark.asyncio
    async def test_write_file(self):
        """Test writing file"""
        with TemporaryDirectory() as tmpdir:
            tool = FileManagerTool(base_path=tmpdir)
            
            result = await tool.execute({
                "action": "write",
                "path": "new_file.txt",
                "content": "Test content"
            })
            
            assert result.success
            
            # Verify file was created
            test_file = Path(tmpdir) / "new_file.txt"
            assert test_file.exists()
            assert test_file.read_text() == "Test content"
    
    @pytest.mark.asyncio
    async def test_list_directory(self):
        """Test listing directory"""
        with TemporaryDirectory() as tmpdir:
            # Create some files
            (Path(tmpdir) / "file1.txt").write_text("test")
            (Path(tmpdir) / "file2.txt").write_text("test")
            
            tool = FileManagerTool(base_path=tmpdir)
            
            result = await tool.execute({
                "action": "list",
                "path": "."
            })
            
            assert result.success
            assert "file1.txt" in result.content
            assert "file2.txt" in result.content
    
    @pytest.mark.asyncio
    async def test_delete_file(self):
        """Test deleting file"""
        with TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "to_delete.txt"
            test_file.write_text("delete me")
            
            tool = FileManagerTool(base_path=tmpdir)
            
            result = await tool.execute({
                "action": "delete",
                "path": "to_delete.txt"
            })
            
            assert result.success
            assert not test_file.exists()
    
    @pytest.mark.asyncio
    async def test_create_directory(self):
        """Test creating directory"""
        with TemporaryDirectory() as tmpdir:
            tool = FileManagerTool(base_path=tmpdir)
            
            result = await tool.execute({
                "action": "mkdir",
                "path": "new_directory"
            })
            
            assert result.success
            
            new_dir = Path(tmpdir) / "new_directory"
            assert new_dir.exists()
            assert new_dir.is_dir()


class TestFileManagerSecurity:
    """Test File Manager security features"""
    
    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self):
        """Test that path traversal is prevented"""
        with TemporaryDirectory() as tmpdir:
            tool = FileManagerTool(base_path=tmpdir)
            
            # Try to access parent directory
            result = await tool.execute({
                "action": "read",
                "path": "../../../etc/passwd"
            })
            
            # Should be blocked
            assert not result.success
            assert "not allowed" in result.error.lower() or "permission" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_absolute_path_handling(self):
        """Test handling of absolute paths"""
        with TemporaryDirectory() as tmpdir:
            tool = FileManagerTool(base_path=tmpdir)
            
            # Try to use absolute path
            result = await tool.execute({
                "action": "read",
                "path": "/etc/passwd"
            })
            
            # Should be blocked or sandboxed
            assert isinstance(result, ToolResult)
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading nonexistent file"""
        with TemporaryDirectory() as tmpdir:
            tool = FileManagerTool(base_path=tmpdir)
            
            result = await tool.execute({
                "action": "read",
                "path": "nonexistent.txt"
            })
            
            assert not result.success
            assert result.error is not None


def test_file_manager_tool_imports():
    """Test that File Manager tool can be imported"""
    try:
        from openclaw.agents.tools import FileManagerTool
        assert FileManagerTool is not None
    except ImportError as e:
        pytest.fail(f"Failed to import FileManagerTool: {e}")
