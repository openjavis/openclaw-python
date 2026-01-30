"""Base tool interface with enhanced features"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """Result from tool execution"""

    success: bool
    content: str
    error: str | None = None
    metadata: dict[str, Any] | None = None
    execution_time_ms: float | None = None


class ToolPermission(str, Enum):
    """Tool permission levels"""

    READ = "read"  # Read-only operations
    WRITE = "write"  # Write/modify operations
    EXECUTE = "execute"  # Execute commands
    NETWORK = "network"  # Network access
    FILESYSTEM = "filesystem"  # File system access
    DANGEROUS = "dangerous"  # Potentially dangerous operations


@dataclass
class ToolConfig:
    """Configuration for tool execution"""

    timeout_seconds: float = 30.0  # Default timeout
    max_output_size: int = 100000  # Max output size in characters
    allowed_permissions: set[ToolPermission] = field(
        default_factory=lambda: {
            ToolPermission.READ,
            ToolPermission.WRITE,
            ToolPermission.EXECUTE,
            ToolPermission.NETWORK,
            ToolPermission.FILESYSTEM,
        }
    )
    sandbox_enabled: bool = False  # Enable sandboxing
    rate_limit_per_minute: int | None = None  # Rate limit


@dataclass
class ToolMetrics:
    """Metrics for tool execution"""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeout_calls: int = 0
    total_execution_time_ms: float = 0.0
    last_called_at: float | None = None

    def record_call(self, success: bool, execution_time_ms: float, timeout: bool = False) -> None:
        """Record a tool call"""
        self.total_calls += 1
        self.total_execution_time_ms += execution_time_ms
        self.last_called_at = time.time()

        if timeout:
            self.timeout_calls += 1
            self.failed_calls += 1
        elif success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

    @property
    def avg_execution_time_ms(self) -> float:
        """Get average execution time"""
        if self.total_calls == 0:
            return 0.0
        return self.total_execution_time_ms / self.total_calls

    @property
    def success_rate(self) -> float:
        """Get success rate (0-1)"""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "timeout_calls": self.timeout_calls,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "success_rate": self.success_rate,
            "last_called_at": self.last_called_at,
        }


class ToolError(Exception):
    """Base exception for tool errors"""

    pass


class ToolTimeoutError(ToolError):
    """Tool execution timed out"""

    pass


class ToolPermissionError(ToolError):
    """Tool permission denied"""

    pass


class ToolValidationError(ToolError):
    """Tool input validation failed"""

    pass


class ToolRateLimitError(ToolError):
    """Tool rate limit exceeded"""

    pass


class AgentTool(ABC):
    """
    Base class for agent tools with enhanced features:
    - Timeout control
    - Permission checking
    - Rate limiting
    - Execution metrics
    - Output size limiting
    """

    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.required_permissions: set[ToolPermission] = set()
        self._config = ToolConfig()
        self._metrics = ToolMetrics()
        self._rate_limit_calls: list[float] = []

    def configure(self, config: ToolConfig) -> None:
        """Configure tool settings"""
        self._config = config

    @property
    def metrics(self) -> ToolMetrics:
        """Get tool metrics"""
        return self._metrics

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Get JSON schema for tool parameters"""
        pass

    async def _execute_impl(self, params: dict[str, Any]) -> ToolResult:
        """
        Internal execution implementation

        Override this method in subclasses if you want to use the built-in
        timeout/permission/rate-limit features. Otherwise, override execute() directly.
        """
        raise NotImplementedError("Subclass must implement either _execute_impl or execute")

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters

        This method handles:
        - Permission checking
        - Rate limiting
        - Timeout control
        - Metrics collection
        - Output size limiting

        Subclasses can either:
        1. Override this method directly (for custom behavior)
        2. Override _execute_impl (to use built-in features)
        """
        start_time = time.time()

        try:
            # Check if subclass overrides execute directly
            # If so, skip the wrapper logic to avoid recursion
            if type(self).execute != AgentTool.execute:
                # Subclass has custom execute, this shouldn't happen
                # but if it does, just call the implementation
                raise NotImplementedError("If overriding execute(), don't call super().execute()")

            # Check permissions
            self._check_permissions()

            # Check rate limit
            self._check_rate_limit()

            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    self._execute_impl(params), timeout=self._config.timeout_seconds
                )
            except TimeoutError:
                execution_time_ms = (time.time() - start_time) * 1000
                self._metrics.record_call(False, execution_time_ms, timeout=True)

                return ToolResult(
                    success=False,
                    content="",
                    error=f"Tool execution timed out after {self._config.timeout_seconds}s",
                    execution_time_ms=execution_time_ms,
                )

            # Limit output size
            if result.content and len(result.content) > self._config.max_output_size:
                result.content = result.content[: self._config.max_output_size]
                result.content += (
                    f"\n\n[Output truncated at {self._config.max_output_size} characters]"
                )

            # Record metrics
            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms
            self._metrics.record_call(result.success, execution_time_ms)

            return result

        except ToolPermissionError as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics.record_call(False, execution_time_ms)
            return ToolResult(
                success=False,
                content="",
                error=f"Permission denied: {e}",
                execution_time_ms=execution_time_ms,
            )

        except ToolRateLimitError as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics.record_call(False, execution_time_ms)
            return ToolResult(
                success=False,
                content="",
                error=f"Rate limit exceeded: {e}",
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self._metrics.record_call(False, execution_time_ms)
            logger.error(f"Tool {self.name} failed: {e}", exc_info=True)
            return ToolResult(
                success=False, content="", error=str(e), execution_time_ms=execution_time_ms
            )

    def _check_permissions(self) -> None:
        """Check if tool has required permissions"""
        missing = self.required_permissions - self._config.allowed_permissions
        if missing:
            raise ToolPermissionError(f"Missing permissions: {', '.join(p.value for p in missing)}")

    def _check_rate_limit(self) -> None:
        """Check rate limit"""
        if not self._config.rate_limit_per_minute:
            return

        now = time.time()
        minute_ago = now - 60

        # Clean old entries
        self._rate_limit_calls = [t for t in self._rate_limit_calls if t > minute_ago]

        # Check limit
        if len(self._rate_limit_calls) >= self._config.rate_limit_per_minute:
            raise ToolRateLimitError(
                f"Rate limit of {self._config.rate_limit_per_minute}/minute exceeded"
            )

        # Record this call
        self._rate_limit_calls.append(now)

    def validate_params(self, params: dict[str, Any]) -> None:
        """
        Validate parameters against schema

        Override in subclass for custom validation
        """
        schema = self.get_schema()
        required = schema.get("required", [])

        for field_name in required:
            if field_name not in params:
                raise ToolValidationError(f"Missing required parameter: {field_name}")

    def to_dict(self) -> dict[str, Any]:
        """Convert tool to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.get_schema(),
            "permissions": [p.value for p in self.required_permissions],
            "timeout_seconds": self._config.timeout_seconds,
            "metrics": self._metrics.to_dict(),
        }


class SafeAgentTool(AgentTool):
    """
    A safer tool base class with stricter defaults

    Use this for tools that should have extra safety measures
    """

    def __init__(self):
        super().__init__()
        self._config = ToolConfig(
            timeout_seconds=10.0,  # Shorter timeout
            max_output_size=50000,  # Smaller output
            sandbox_enabled=True,
            rate_limit_per_minute=30,  # Default rate limit
        )


# Tool registry for managing available tools
class ToolRegistry:
    """Registry for managing tools"""

    def __init__(self):
        self._tools: dict[str, AgentTool] = {}
        self._global_config: ToolConfig | None = None

    def set_global_config(self, config: ToolConfig) -> None:
        """Set global configuration for all tools"""
        self._global_config = config
        for tool in self._tools.values():
            tool.configure(config)

    def register(self, tool: AgentTool) -> None:
        """Register a tool"""
        if self._global_config:
            tool.configure(self._global_config)
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        """Unregister a tool"""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")

    def get(self, name: str) -> AgentTool | None:
        """Get a tool by name"""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names"""
        return list(self._tools.keys())

    def get_all(self) -> list[AgentTool]:
        """Get all registered tools"""
        return list(self._tools.values())

    def get_metrics(self) -> dict[str, dict]:
        """Get metrics for all tools"""
        return {name: tool.metrics.to_dict() for name, tool in self._tools.items()}


# Global tool registry
_tool_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry"""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
