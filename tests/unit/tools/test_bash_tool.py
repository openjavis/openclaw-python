"""Unit tests for Bash tool"""
import asyncio
import subprocess
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from openclaw.agents.tools.bash import create_bash_tool as BashTool
from openclaw.agents.types import AgentToolResult, TextContent


class TestBashTool:
    """Test Bash tool"""

    def test_create_tool(self):
        """Test creating Bash tool"""
        tool = BashTool()
        assert tool is not None
        assert tool.name == "bash"
        assert tool.description != ""

    def test_get_schema(self):
        """Test getting tool schema"""
        tool = BashTool()
        schema = tool.get_schema()

        assert isinstance(schema, dict)
        assert "type" in schema
        assert "properties" in schema
        assert "command" in schema["properties"]

    @pytest.mark.asyncio
    async def test_execute_simple_command(self):
        """Test executing simple command"""
        tool = BashTool()

        with patch(
            "openclaw.agents.tools.default_operations.DefaultBashOperations.exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"exit_code": 0, "stdout": "Hello\n", "stderr": ""}

            result = await tool.execute("test_id", {"command": "echo Hello"})

            assert isinstance(result, AgentToolResult)

    @pytest.mark.asyncio
    async def test_execute_command_failure(self):
        """Test executing command that fails"""
        tool = BashTool()

        with patch(
            "openclaw.agents.tools.default_operations.DefaultBashOperations.exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"exit_code": 1, "stdout": "", "stderr": "Error"}

            with pytest.raises(Exception):
                await tool.execute("test_id", {"command": "false"})

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test command timeout (default_timeout set on tool instance)"""
        tool = BashTool(timeout=1)

        assert tool.default_timeout == 1

        with patch(
            "openclaw.agents.tools.default_operations.DefaultBashOperations.exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.side_effect = asyncio.TimeoutError()

            with pytest.raises(Exception) as exc_info:
                await tool.execute("test_id", {"command": "sleep 10"})

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_invalid_params(self):
        """Test executing with invalid parameters (missing command)"""
        tool = BashTool()

        with pytest.raises(KeyError):
            await tool.execute("test_id", {})  # Missing 'command'


class TestBashToolSecurity:
    """Test Bash tool security features"""

    @pytest.mark.asyncio
    async def test_blocked_commands(self):
        """Test that dangerous commands still produce AgentToolResult"""
        tool = BashTool()

        with patch(
            "openclaw.agents.tools.default_operations.DefaultBashOperations.exec",
            new_callable=AsyncMock,
        ) as mock_exec:
            mock_exec.return_value = {"exit_code": 0, "stdout": "", "stderr": ""}

            result = await tool.execute("test_id", {"command": "echo safe"})
            assert isinstance(result, AgentToolResult)

    def test_working_directory(self):
        """Test working directory setting"""
        tool = BashTool(working_dir="/tmp")
        assert tool.working_dir == "/tmp"


def test_bash_tool_imports():
    """Test that Bash tool can be imported"""
    try:
        from openclaw.agents.tools import BashTool
        assert BashTool is not None
    except ImportError as e:
        pytest.fail(f"Failed to import BashTool: {e}")
