"""
Tests for Tool Base Classes
"""

import pytest

from openclaw.agents.tools.base import AgentTool, ToolResult


class TestToolResult:
    """Test ToolResult class"""

    def test_result_creation(self):
        """Test creating a tool result"""
        result = ToolResult(success=True, content="Success", error=None)
        assert result.success is True
        assert result.content == "Success"
        assert result.error is None

    def test_result_with_error(self):
        """Test result with error"""
        result = ToolResult(success=False, content="", error="Failed")
        assert result.success is False
        assert result.content == ""
        assert result.error == "Failed"


class MockTool(AgentTool):
    """Mock tool for testing"""

    def __init__(self):
        super().__init__()
        self.name = "mock_tool"
        self.description = "A mock tool for testing"

    def get_schema(self):
        return {
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"],
        }

    async def _execute_impl(self, params):
        if params.get("param") == "error":
            return ToolResult(success=False, content="", error="Mock error")
        return ToolResult(success=True, content=f"Executed with {params}", error=None)


class TestAgentTool:
    """Test AgentTool base class"""

    def test_tool_creation(self):
        """Test creating a tool"""
        tool = MockTool()
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"

    def test_tool_schema(self):
        """Test getting tool schema"""
        tool = MockTool()
        schema = tool.get_schema()

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "param" in schema["properties"]

    @pytest.mark.asyncio
    async def test_tool_execute_success(self):
        """Test successful tool execution"""
        tool = MockTool()
        result = await tool.execute({"param": "test"})

        assert result.error is None
        assert "test" in result.content

    @pytest.mark.asyncio
    async def test_tool_execute_error(self):
        """Test tool execution with error"""
        tool = MockTool()
        result = await tool.execute({"param": "error"})

        assert result.error == "Mock error"
        assert result.content == ""
