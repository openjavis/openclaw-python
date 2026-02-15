"""
Unit tests for Agent Loop - aligned with pi-mono

Tests the double-loop architecture, steering, and follow-up mechanisms.
"""
import asyncio
import pytest

from openclaw.agents.agent_loop import (
    AgentLoop,
    AgentOptions,
    AgentMessage,
    default_convert_to_llm,
)
from openclaw.agents.events import EventEmitter
from openclaw.agents.tools.base import AgentTool, ToolResult


# Mock tool for testing
class MockTool(AgentTool):
    """Mock tool for testing"""
    
    name = "mock_tool"
    description = "A mock tool for testing"
    
    def __init__(self):
        self.execution_count = 0
    
    async def execute(self, tool_call_id: str, params: dict, signal=None, on_update=None) -> ToolResult:
        """Mock execution"""
        self.execution_count += 1
        return ToolResult(
            success=True,
            content=f"Mock result {self.execution_count}"
        )
    
    def get_schema(self) -> dict:
        """Get tool schema"""
        return {
            "type": "object",
            "properties": {},
            "required": []
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
