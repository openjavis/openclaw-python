"""
Tool Definition Adapter - adapts tool definitions for agent runtime

Aligned with openclaw/src/agents/pi-tool-definition-adapter.ts
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class ToolDefinitionAdapter:
    """
    Tool definition adapter for agent runtime
    
    Wraps tool execution with error handling and standardizes tool definitions.
    Matches TypeScript ToolDefinitionAdapter functionality.
    """
    
    @staticmethod
    def to_tool_definitions(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Convert tools to standardized definitions
        
        Args:
            tools: Raw tool definitions
            
        Returns:
            Standardized tool definitions with wrapped execute functions
        """
        adapted_tools = []
        
        for tool in tools:
            if not tool.get("name"):
                logger.warning(f"Skipping tool without name: {tool}")
                continue
            
            adapted_tool = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {}),
            }
            
            # Wrap execute function if present
            if "execute" in tool:
                adapted_tool["execute"] = ToolDefinitionAdapter._wrap_execute(
                    tool["execute"],
                    tool["name"]
                )
            
            adapted_tools.append(adapted_tool)
        
        return adapted_tools
    
    @staticmethod
    def _wrap_execute(execute_fn: Callable, tool_name: str) -> Callable[..., Awaitable[Any]]:
        """
        Wrap tool execute function with error handling
        
        Args:
            execute_fn: Original execute function
            tool_name: Tool name for logging
            
        Returns:
            Wrapped execute function
        """
        async def wrapped(**kwargs):
            try:
                # Handle both sync and async execute functions
                result = execute_fn(**kwargs)
                
                # Await if coroutine
                if hasattr(result, '__await__'):
                    result = await result
                
                # Ensure result is in standard format
                if not isinstance(result, dict):
                    result = {"content": str(result), "success": True}
                elif "success" not in result:
                    result["success"] = True
                
                return result
                
            except Exception as e:
                logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
                return {
                    "error": str(e),
                    "success": False,
                    "content": f"Error executing {tool_name}: {str(e)}"
                }
        
        return wrapped
    
    @staticmethod
    def validate_tool_definition(tool: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate tool definition structure
        
        Args:
            tool: Tool definition
            
        Returns:
            (is_valid, error_message)
        """
        # Check required fields
        if "name" not in tool:
            return False, "Tool missing 'name' field"
        
        if not isinstance(tool["name"], str):
            return False, "Tool 'name' must be string"
        
        # Check parameters structure if present
        if "parameters" in tool:
            params = tool["parameters"]
            if not isinstance(params, dict):
                return False, "Tool 'parameters' must be dict"
            
            # Validate JSON Schema structure
            if "type" in params and params["type"] != "object":
                return False, "Tool parameters 'type' must be 'object'"
        
        return True, None
    
    @staticmethod
    def filter_tools_by_names(
        tools: list[dict[str, Any]],
        allowed_names: list[str] | None = None,
        blocked_names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Filter tools by name allowlist/blocklist
        
        Args:
            tools: Tool definitions
            allowed_names: If provided, only include these tools
            blocked_names: If provided, exclude these tools
            
        Returns:
            Filtered tools
        """
        filtered = tools
        
        if allowed_names is not None:
            filtered = [t for t in filtered if t["name"] in allowed_names]
        
        if blocked_names is not None:
            filtered = [t for t in filtered if t["name"] not in blocked_names]
        
        return filtered


def sanitize_tools_for_provider(
    tools: list[dict[str, Any]],
    provider: str
) -> list[dict[str, Any]]:
    """
    Sanitize tools for specific provider requirements
    
    Different providers have different requirements for tool definitions.
    
    Args:
        tools: Tool definitions
        provider: Provider name (gemini, anthropic, openai, etc.)
        
    Returns:
        Sanitized tools
    """
    if provider.lower() in ["gemini", "google"]:
        # Gemini schema cleaning is handled in gemini_provider.py
        # using clean_schema_for_gemini() to remove unsupported keywords
        return tools
    
    elif provider.lower() in ["anthropic", "claude"]:
        # Anthropic requires input_schema instead of parameters
        sanitized = []
        for tool in tools:
            sanitized_tool = tool.copy()
            if "parameters" in sanitized_tool:
                sanitized_tool["input_schema"] = sanitized_tool.pop("parameters")
            sanitized.append(sanitized_tool)
        return sanitized
    
    # Default: return as-is
    return tools


def split_sdk_tools(
    tools: list[dict[str, Any]],
    sandbox_enabled: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """
    Split tools into built-in SDK tools and custom tools
    
    Args:
        tools: All tool definitions
        sandbox_enabled: Whether sandbox is enabled
        
    Returns:
        Dict with "builtInTools" and "customTools" keys
    """
    built_in_names = {
        "read", "write", "edit", "search",
        "exec", "bash", "shell",
        "list_files", "glob",
    }
    
    built_in = []
    custom = []
    
    for tool in tools:
        name = tool.get("name", "")
        if name in built_in_names:
            built_in.append(tool)
        else:
            custom.append(tool)
    
    return {
        "builtInTools": built_in,
        "customTools": custom
    }
