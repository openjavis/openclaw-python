"""
Direct tool invocation endpoint.

Provides /tools/invoke endpoint for executing tools without full agent turn.
Always enabled, gated by auth and tool policy.

Reference: openclaw/docs/gateway/http-tools-invoke.md
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ToolInvokeRequest(BaseModel):
    """Tool invocation request"""
    
    tool: str  # Tool name
    params: dict[str, Any]
    context: dict[str, Any] | None = None


class ToolInvokeResponse(BaseModel):
    """Tool invocation response"""
    
    ok: bool
    result: Any | None = None
    details: Any | None = None
    error: dict[str, Any] | None = None


def check_tool_policy(tool_name: str, config) -> bool:
    """
    Check if tool is allowed by policy.
    
    Args:
        tool_name: Tool name
        config: Gateway config
        
    Returns:
        True if tool is allowed, False otherwise
    """
    # Check global allow list
    tools_config = getattr(config, 'tools', None)
    if tools_config:
        allow_list = getattr(tools_config, 'allow', None)
        if allow_list and tool_name not in allow_list:
            return False
        
        deny_list = getattr(tools_config, 'deny', None)
        if deny_list and tool_name in deny_list:
            return False
    
    return True


async def handle_tool_invoke(
    request: ToolInvokeRequest,
    tool_registry,
    config,
    authorization: str | None = None
) -> ToolInvokeResponse:
    """
    Handle tool invocation request.
    
    Args:
        request: Tool invoke request
        tool_registry: Tool registry
        config: Gateway config
        authorization: Authorization header
        
    Returns:
        Tool invocation response
    """
    try:
        # Check tool policy
        if not check_tool_policy(request.tool, config):
            return ToolInvokeResponse(
                ok=False,
                error={
                    "code": "FORBIDDEN",
                    "message": f"Tool '{request.tool}' not allowed by policy"
                }
            )
        
        # Get tool from registry
        tool = tool_registry.get(request.tool)
        if not tool:
            return ToolInvokeResponse(
                ok=False,
                error={
                    "code": "NOT_FOUND",
                    "message": f"Tool '{request.tool}' not found"
                }
            )
        
        # Execute tool
        result = await tool.execute(
            tool_call_id="http_invoke",
            params=request.params,
            signal=None,
            on_update=None
        )
        
        return ToolInvokeResponse(
            ok=True,
            result=result.content,
            details=result.details
        )
        
    except Exception as e:
        return ToolInvokeResponse(
            ok=False,
            error={
                "code": "EXECUTION_ERROR",
                "message": str(e)
            }
        )


__all__ = [
    "ToolInvokeRequest",
    "ToolInvokeResponse",
    "handle_tool_invoke",
]
