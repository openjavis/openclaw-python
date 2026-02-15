"""
Tool system matching pi-mono's tool interface

This module provides the tool interface and base classes for:
- Tool definition with streaming support
- Tool execution with on_update callbacks
- Tool results with content/details separation
- Parameter validation

Matches pi-mono/packages/agent/src/types.ts AgentTool interface
"""
from __future__ import annotations

import asyncio
import logging
import warnings
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel

from ..types import AgentToolResult, Content, TextContent

logger = logging.getLogger(__name__)

TParams = TypeVar("TParams")
TDetails = TypeVar("TDetails")


class LegacyToolResult(BaseModel):
    """
    Legacy tool result format (for backward compatibility).
    
    This is the old format used by existing tools. LegacyAgentTool.execute()
    converts this to AgentToolResult automatically.
    """
    success: bool
    content: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = {}


class AgentToolBase(ABC, Generic[TParams, TDetails]):
    """
    Base class for agent tools matching Pi Agent's interface.
    
    Tools must implement:
    - name: Tool identifier for LLM
    - label: Human-readable name for UI
    - description: What the tool does (for LLM)
    - parameters: JSON Schema for parameters
    - execute: Async execution with streaming support
    
    Example:
        ```python
        class ReadFileTool(AgentToolBase[dict, dict]):
            @property
            def name(self) -> str:
                return "read"
            
            @property
            def label(self) -> str:
                return "Read File"
            
            @property
            def description(self) -> str:
                return "Read contents of a file"
            
            @property
            def parameters(self) -> dict:
                return {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to read"
                        }
                    },
                    "required": ["path"]
                }
            
            async def execute(
                self,
                tool_call_id: str,
                params: dict,
                signal: asyncio.Event | None = None,
                on_update: Callable[[AgentToolResult], None] | None = None,
            ) -> AgentToolResult[dict]:
                path = params["path"]
                
                # Check cancellation
                if signal and signal.is_set():
                    raise asyncio.CancelledError()
                
                # Read file
                with open(path) as f:
                    content = f.read()
                
                # Return result
                return AgentToolResult(
                    content=[TextContent(text=content)],
                    details={"path": path, "size": len(content)}
                )
        ```
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name (identifier for LLM).
        
        Should be lowercase, no spaces (e.g. "read", "write", "bash")
        """
        ...
    
    @property
    @abstractmethod
    def label(self) -> str:
        """
        Human-readable label for UI.
        
        Example: "Read File", "Execute Bash", "Search Files"
        """
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Tool description for LLM.
        
        Should clearly explain:
        - What the tool does
        - When to use it
        - What it returns
        """
        ...
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """
        JSON Schema for tool parameters.
        
        Must be valid JSON Schema with:
        - type: "object"
        - properties: parameter definitions
        - required: list of required parameter names
        
        Example:
            ```python
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max lines to read",
                        "default": 100
                    }
                },
                "required": ["path"]
            }
            ```
        """
        ...
    
    def get_schema(self) -> dict[str, Any]:
        """
        Get JSON Schema for tool parameters (backward compatibility).
        
        Returns the same as self.parameters.
        """
        return self.parameters
    
    @abstractmethod
    async def execute(
        self,
        tool_call_id: str,
        params: TParams,
        signal: asyncio.Event | None = None,
        on_update: Callable[[AgentToolResult[TDetails]], None] | None = None,
    ) -> AgentToolResult[TDetails]:
        """
        Execute tool with streaming support.
        
        Args:
            tool_call_id: Unique ID for this invocation
            params: Validated parameters (matching schema)
            signal: Cancellation signal (check with signal.is_set())
            on_update: Callback for streaming progress updates
            
        Returns:
            Tool execution result with content and details
            
        Raises:
            asyncio.CancelledError: If signal is set during execution
            Exception: Other errors are caught and reported
            
        Example:
            ```python
            async def execute(self, tool_call_id, params, signal, on_update):
                # Check cancellation periodically
                if signal and signal.is_set():
                    raise asyncio.CancelledError()
                
                # For long operations, send progress updates
                if on_update:
                    on_update(AgentToolResult(
                        content=[TextContent(text="Processing...")],
                        details={"progress": 0.5}
                    ))
                
                # Do work
                result = await do_work(params)
                
                # Return final result
                return AgentToolResult(
                    content=[TextContent(text=result)],
                    details={"metadata": "for UI"}
                )
            ```
        """
        ...


class SimpleTool(AgentToolBase[dict, dict]):
    """
    Simple tool implementation with function-based execution.
    
    Convenient for creating tools without subclassing.
    
    Example:
        ```python
        async def read_file(tool_call_id, params, signal, on_update):
            path = params["path"]
            with open(path) as f:
                content = f.read()
            return AgentToolResult(
                content=[TextContent(text=content)],
                details={"path": path}
            )
        
        tool = SimpleTool(
            name="read",
            label="Read File",
            description="Read contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            },
            execute_fn=read_file
        )
        ```
    """
    
    def __init__(
        self,
        name: str,
        label: str,
        description: str,
        parameters: dict[str, Any],
        execute_fn: Callable[
            [str, dict, asyncio.Event | None, Callable[[AgentToolResult], None] | None],
            AgentToolResult
        ],
    ):
        """
        Initialize simple tool.
        
        Args:
            name: Tool name
            label: UI label
            description: Tool description
            parameters: JSON Schema
            execute_fn: Execution function
        """
        self._name = name
        self._label = label
        self._description = description
        self._parameters = parameters
        self._execute_fn = execute_fn
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def label(self) -> str:
        return self._label
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters
    
    async def execute(
        self,
        tool_call_id: str,
        params: dict,
        signal: asyncio.Event | None = None,
        on_update: Callable[[AgentToolResult], None] | None = None,
    ) -> AgentToolResult[dict]:
        return await self._execute_fn(tool_call_id, params, signal, on_update)


def validate_tool_parameters(tool: AgentToolBase, params: dict) -> dict:
    """
    Validate tool parameters against schema.
    
    This is a basic validation - for production, should use jsonschema library.
    
    Args:
        tool: Tool to validate against
        params: Parameters to validate
        
    Returns:
        Validated parameters (may have defaults applied)
        
    Raises:
        ValueError: If validation fails
    """
    schema = tool.parameters
    
    # Check required parameters
    required = schema.get("required", [])
    for param in required:
        if param not in params:
            raise ValueError(f"Missing required parameter: {param}")
    
    # Basic type checking (simplified)
    properties = schema.get("properties", {})
    for key, value in params.items():
        if key not in properties:
            logger.warning(f"Unknown parameter: {key}")
            continue
        
        prop_schema = properties[key]
        expected_type = prop_schema.get("type")
        
        # Basic type validation
        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"Parameter {key} must be string, got {type(value).__name__}")
        elif expected_type == "integer" and not isinstance(value, int):
            raise ValueError(f"Parameter {key} must be integer, got {type(value).__name__}")
        elif expected_type == "number" and not isinstance(value, (int, float)):
            raise ValueError(f"Parameter {key} must be number, got {type(value).__name__}")
        elif expected_type == "boolean" and not isinstance(value, bool):
            raise ValueError(f"Parameter {key} must be boolean, got {type(value).__name__}")
        elif expected_type == "array" and not isinstance(value, list):
            raise ValueError(f"Parameter {key} must be array, got {type(value).__name__}")
        elif expected_type == "object" and not isinstance(value, dict):
            raise ValueError(f"Parameter {key} must be object, got {type(value).__name__}")
    
    return params


# Legacy tool base class for backward compatibility
class LegacyAgentTool:
    """
    Legacy tool base class that supports old API.
    
    **DEPRECATED**: Use AgentToolBase instead for new tools.
    
    This class is provided for backward compatibility only.
    It will be removed in a future version.
    
    Subclasses should:
    - Set self.name, self.description in __init__
    - Implement get_schema() -> dict
    - Implement async _execute_impl(params) -> ToolResult
    """
    
    def __init__(self):
        warnings.warn(
            "LegacyAgentTool is deprecated and will be removed in a future version. "
            "Use AgentToolBase instead for new tools. "
            "See openclaw/agents/tools/README.md for migration guide.",
            DeprecationWarning,
            stacklevel=2
        )
        self.name = ""
        self.description = ""
    
    @property
    def label(self) -> str:
        """Default label from name"""
        return self.name.replace("_", " ").title()
    
    @property
    def parameters(self) -> dict[str, Any]:
        """Get parameters from get_schema()"""
        if hasattr(self, "get_schema"):
            return self.get_schema()
        return {"type": "object", "properties": {}, "required": []}
    
    async def execute(
        self,
        tool_call_id: str,
        params: dict,
        signal: asyncio.Event | None = None,
        on_update: Callable[[AgentToolResult], None] | None = None,
    ) -> AgentToolResult:
        """Execute via _execute_impl"""
        if hasattr(self, "_execute_impl"):
            result = await self._execute_impl(params)
            # Convert LegacyToolResult to AgentToolResult
            if isinstance(result, AgentToolResult):
                return result
            # Convert legacy ToolResult
            if isinstance(result, LegacyToolResult):
                if result.success:
                    content_text = result.content or ""
                    return AgentToolResult(
                        content=[TextContent(text=content_text)],
                        details={
                            "success": True,
                            **result.metadata
                        }
                    )
                else:
                    error_text = result.error or "Error"
                    return AgentToolResult(
                        content=[TextContent(text=error_text)],
                        details={
                            "success": False,
                            "error": result.error,
                            **result.metadata
                        }
                    )
        raise NotImplementedError("_execute_impl not implemented")


# Backward compatibility aliases
AgentTool = LegacyAgentTool
ToolResult = LegacyToolResult  # Old tools use LegacyToolResult

__all__ = [
    "AgentToolBase",
    "LegacyAgentTool",
    "LegacyToolResult",
    "AgentTool",
    "AgentToolResult",
    "ToolResult",
    "SimpleTool",
    "validate_tool_parameters",
]
