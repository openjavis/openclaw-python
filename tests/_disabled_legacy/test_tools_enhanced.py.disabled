"""
Tests for enhanced tool system
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from openclaw.agents.tools.base import (
    AgentTool,
    ToolConfig,
    ToolMetrics,
    ToolPermission,
    ToolPermissionError,
    ToolRateLimitError,
    ToolRegistry,
    ToolResult,
    ToolTimeoutError,
    get_tool_registry,
)


class MockTool(AgentTool):
    """Mock tool for testing"""

    def __init__(self, delay: float = 0.0, should_fail: bool = False):
        super().__init__()
        self.name = "mock_tool"
        self.description = "A mock tool for testing"
        self.delay = delay
        self.should_fail = should_fail
        self.required_permissions = {ToolPermission.READ}

    def get_schema(self):
        return {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
        }

    async def _execute_impl(self, params):
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.should_fail:
            return ToolResult(success=False, content="", error="Mock failure")

        return ToolResult(success=True, content=f"Result: {params.get('input', '')}")


class TestToolResult:
    """Test ToolResult class"""

    def test_result_success(self):
        result = ToolResult(success=True, content="output")
        assert result.success
        assert result.content == "output"
        assert result.error is None

    def test_result_failure(self):
        result = ToolResult(success=False, content="", error="failed")
        assert not result.success
        assert result.error == "failed"

    def test_result_with_metadata(self):
        result = ToolResult(
            success=True, content="output", metadata={"key": "value"}, execution_time_ms=100.5
        )
        assert result.metadata == {"key": "value"}
        assert result.execution_time_ms == 100.5


class TestToolConfig:
    """Test ToolConfig class"""

    def test_default_config(self):
        config = ToolConfig()
        assert config.timeout_seconds == 30.0
        assert config.max_output_size == 100000
        assert ToolPermission.READ in config.allowed_permissions

    def test_custom_config(self):
        config = ToolConfig(
            timeout_seconds=10.0,
            max_output_size=5000,
            allowed_permissions={ToolPermission.READ},
            rate_limit_per_minute=60,
        )
        assert config.timeout_seconds == 10.0
        assert config.rate_limit_per_minute == 60


class TestToolMetrics:
    """Test ToolMetrics class"""

    def test_initial_metrics(self):
        metrics = ToolMetrics()
        assert metrics.total_calls == 0
        assert metrics.success_rate == 0.0

    def test_record_success(self):
        metrics = ToolMetrics()
        metrics.record_call(True, 100.0)

        assert metrics.total_calls == 1
        assert metrics.successful_calls == 1
        assert metrics.failed_calls == 0
        assert metrics.avg_execution_time_ms == 100.0

    def test_record_failure(self):
        metrics = ToolMetrics()
        metrics.record_call(False, 50.0)

        assert metrics.total_calls == 1
        assert metrics.failed_calls == 1
        assert metrics.success_rate == 0.0

    def test_record_timeout(self):
        metrics = ToolMetrics()
        metrics.record_call(False, 30000.0, timeout=True)

        assert metrics.timeout_calls == 1
        assert metrics.failed_calls == 1

    def test_multiple_calls(self):
        metrics = ToolMetrics()
        metrics.record_call(True, 100.0)
        metrics.record_call(True, 200.0)
        metrics.record_call(False, 50.0)

        assert metrics.total_calls == 3
        assert metrics.successful_calls == 2
        assert metrics.failed_calls == 1
        assert metrics.success_rate == pytest.approx(2 / 3)


class TestAgentTool:
    """Test AgentTool class"""

    @pytest.mark.asyncio
    async def test_execute_success(self):
        tool = MockTool()
        result = await tool.execute({"input": "test"})

        assert result.success
        assert "test" in result.content
        assert result.execution_time_ms is not None

    @pytest.mark.asyncio
    async def test_execute_failure(self):
        tool = MockTool(should_fail=True)
        result = await tool.execute({"input": "test"})

        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        tool = MockTool(delay=5.0)
        tool.configure(ToolConfig(timeout_seconds=0.1))

        result = await tool.execute({"input": "test"})

        assert not result.success
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_permission_denied(self):
        tool = MockTool()
        tool.required_permissions = {ToolPermission.DANGEROUS}
        tool.configure(ToolConfig(allowed_permissions={ToolPermission.READ}))

        result = await tool.execute({"input": "test"})

        assert not result.success
        assert "permission" in result.error.lower()

    @pytest.mark.asyncio
    async def test_rate_limit(self):
        tool = MockTool()
        tool.configure(ToolConfig(rate_limit_per_minute=2))

        # First two should succeed
        result1 = await tool.execute({"input": "1"})
        result2 = await tool.execute({"input": "2"})

        assert result1.success
        assert result2.success

        # Third should be rate limited
        result3 = await tool.execute({"input": "3"})

        assert not result3.success
        assert "rate limit" in result3.error.lower()

    @pytest.mark.asyncio
    async def test_output_truncation(self):
        class LongOutputTool(AgentTool):
            def __init__(self):
                super().__init__()
                self.name = "long_output"
                self.description = "Tool with long output"

            def get_schema(self):
                return {"type": "object", "properties": {}}

            async def _execute_impl(self, params):
                return ToolResult(success=True, content="x" * 200000)

        tool = LongOutputTool()
        tool.configure(ToolConfig(max_output_size=1000))

        result = await tool.execute({})

        assert result.success
        assert len(result.content) <= 1100  # Some buffer for truncation message
        assert "truncated" in result.content.lower()

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        tool = MockTool()

        await tool.execute({"input": "1"})
        await tool.execute({"input": "2"})

        assert tool.metrics.total_calls == 2
        assert tool.metrics.successful_calls == 2

    def test_to_dict(self):
        tool = MockTool()
        data = tool.to_dict()

        assert data["name"] == "mock_tool"
        assert "parameters" in data
        assert "metrics" in data


class TestToolRegistry:
    """Test ToolRegistry class"""

    def test_register_tool(self):
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)

        assert "mock_tool" in registry.list_tools()
        assert registry.get("mock_tool") == tool

    def test_unregister_tool(self):
        registry = ToolRegistry()
        tool = MockTool()

        registry.register(tool)
        registry.unregister("mock_tool")

        assert "mock_tool" not in registry.list_tools()
        assert registry.get("mock_tool") is None

    def test_get_all_tools(self):
        registry = ToolRegistry()
        tool1 = MockTool()
        tool1.name = "tool1"
        tool2 = MockTool()
        tool2.name = "tool2"

        registry.register(tool1)
        registry.register(tool2)

        all_tools = registry.get_all()
        assert len(all_tools) == 2

    def test_set_global_config(self):
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        config = ToolConfig(timeout_seconds=5.0)
        registry.set_global_config(config)

        assert tool._config.timeout_seconds == 5.0

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        registry = ToolRegistry()
        tool = MockTool()
        registry.register(tool)

        await tool.execute({"input": "test"})

        metrics = registry.get_metrics()
        assert "mock_tool" in metrics
        assert metrics["mock_tool"]["total_calls"] == 1
