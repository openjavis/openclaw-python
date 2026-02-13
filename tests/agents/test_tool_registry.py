"""
Unit tests for ToolRegistry

Tests tool registration, lookup, and management.
"""

import pytest
from openclaw.agents.tools.base import AgentToolBase
from openclaw.agents.tools.registry import ToolRegistry


class MockTool(AgentToolBase):
    """Mock tool for testing."""
    name = "mock_tool"
    description = "A mock tool for testing"
    
    async def execute(self, **kwargs):
        return {"result": "mock_result"}
    
    def get_schema(self):
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            }
        }


class AnotherMockTool(AgentToolBase):
    """Another mock tool."""
    name = "another_tool"
    description = "Another tool"
    
    async def execute(self, **kwargs):
        return {"result": "another_result"}
    
    def get_schema(self):
        return {"type": "object", "properties": {}}


class TestToolRegistration:
    """Test tool registration."""
    
    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register(tool)
        
        assert "mock_tool" in registry._tools
        assert registry._tools["mock_tool"] is tool
    
    def test_register_multiple_tools(self):
        """Test registering multiple tools."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = AnotherMockTool()
        
        registry.register(tool1)
        registry.register(tool2)
        
        assert len(registry._tools) == 2
        assert "mock_tool" in registry._tools
        assert "another_tool" in registry._tools
    
    def test_register_duplicate_name_raises(self):
        """Test that registering duplicate names raises error."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockTool()  # Same name
        
        registry.register(tool1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)
    
    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register(tool)
        registry.unregister("mock_tool")
        
        assert "mock_tool" not in registry._tools
    
    def test_unregister_nonexistent_tool(self):
        """Test unregistering a tool that doesn't exist."""
        registry = ToolRegistry()
        
        # Should not raise error
        registry.unregister("nonexistent")


class TestToolLookup:
    """Test tool lookup and retrieval."""
    
    def test_get_tool_by_name(self):
        """Test getting a tool by name."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        
        found = registry.get("mock_tool")
        
        assert found is tool
    
    def test_get_nonexistent_tool_returns_none(self):
        """Test getting a nonexistent tool returns None."""
        registry = ToolRegistry()
        
        found = registry.get("nonexistent")
        
        assert found is None
    
    def test_has_tool(self):
        """Test checking if tool exists."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        
        assert registry.has("mock_tool") is True
        assert registry.has("nonexistent") is False
    
    def test_list_all_tools(self):
        """Test listing all registered tools."""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = AnotherMockTool()
        
        registry.register(tool1)
        registry.register(tool2)
        
        tools = registry.list()
        
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools
    
    def test_list_tool_names(self):
        """Test listing tool names."""
        registry = ToolRegistry()
        registry.register(MockTool())
        registry.register(AnotherMockTool())
        
        names = registry.list_names()
        
        assert "mock_tool" in names
        assert "another_tool" in names
        assert len(names) == 2


class TestToolExecution:
    """Test tool execution through registry."""
    
    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test executing a tool through registry."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        
        result = await registry.execute("mock_tool", input="test")
        
        assert result["result"] == "mock_result"
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool_raises(self):
        """Test executing nonexistent tool raises error."""
        registry = ToolRegistry()
        
        with pytest.raises(KeyError):
            await registry.execute("nonexistent")


class TestToolSchemas:
    """Test tool schema retrieval."""
    
    def test_get_tool_schema(self):
        """Test getting tool schema."""
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)
        
        schema = registry.get_schema("mock_tool")
        
        assert schema is not None
        assert "properties" in schema
    
    def test_get_all_schemas(self):
        """Test getting all tool schemas."""
        registry = ToolRegistry()
        registry.register(MockTool())
        registry.register(AnotherMockTool())
        
        schemas = registry.get_all_schemas()
        
        assert len(schemas) == 2
        assert "mock_tool" in schemas
        assert "another_tool" in schemas


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
