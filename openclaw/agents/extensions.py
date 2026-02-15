"""
Tool wrapping and extension system - aligned with coding-agent core/extensions/wrapper.ts

Provides extension hooks for intercepting and modifying tool calls and results.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Literal, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ToolCallEvent:
    """
    Tool call event - aligned with coding-agent
    
    Emitted before tool execution. Extensions can block execution.
    """
    type: Literal["tool_call"] = "tool_call"
    tool_name: str
    tool_call_id: str
    input: Dict[str, Any]


@dataclass
class ToolCallEventResult:
    """
    Tool call event result from extension
    
    Extensions return this to indicate whether to block execution.
    """
    block: bool = False  # If True, tool execution is blocked
    reason: str | None = None  # Reason for blocking


@dataclass
class ToolResultEvent:
    """
    Tool result event - aligned with coding-agent
    
    Emitted after tool execution. Extensions can modify results.
    """
    type: Literal["tool_result"] = "tool_result"
    tool_name: str
    tool_call_id: str
    input: Dict[str, Any]
    content: List[Dict[str, Any]]  # Result content
    details: Any  # Additional details
    is_error: bool


@dataclass
class ToolResultModification:
    """
    Tool result modification from extension
    
    Extensions can return this to modify tool results.
    """
    content: List[Dict[str, Any]] | None = None
    details: Any | None = None


class ExtensionRunner:
    """
    Extension runner - aligned with coding-agent ExtensionRunner
    
    Manages extension hooks for tool calls and results.
    Supports both sync and async handlers.
    """
    
    def __init__(self):
        """Initialize extension runner"""
        self._handlers: Dict[str, List[Callable]] = {
            "tool_call": [],
            "tool_result": [],
        }
    
    def has_handlers(self, event_type: str) -> bool:
        """
        Check if there are handlers for an event type
        
        Args:
            event_type: Event type ("tool_call" or "tool_result")
            
        Returns:
            True if handlers are registered
        """
        return len(self._handlers.get(event_type, [])) > 0
    
    def on(self, event_type: str, handler: Callable) -> None:
        """
        Register an extension handler
        
        Args:
            event_type: Event type ("tool_call" or "tool_result")
            handler: Handler function (sync or async)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered {event_type} handler: {handler.__name__}")
    
    def off(self, event_type: str, handler: Callable) -> None:
        """
        Unregister an extension handler
        
        Args:
            event_type: Event type
            handler: Handler to remove
        """
        if event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Unregistered {event_type} handler: {handler.__name__}")
    
    async def emit_tool_call(self, event: ToolCallEvent) -> ToolCallEventResult | None:
        """
        Emit tool_call event - aligned with coding-agent
        
        Handlers can block tool execution by returning ToolCallEventResult(block=True).
        If any handler blocks, execution is prevented.
        
        Args:
            event: Tool call event
            
        Returns:
            ToolCallEventResult if execution should be blocked, None otherwise
        """
        handlers = self._handlers.get("tool_call", [])
        
        for handler in handlers:
            try:
                # Handle both sync and async handlers
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)
                
                # Check if handler wants to block
                if result and isinstance(result, ToolCallEventResult) and result.block:
                    logger.info(
                        f"Tool call blocked by extension: {event.tool_name} "
                        f"(reason: {result.reason})"
                    )
                    return result
                    
            except Exception as e:
                logger.error(
                    f"Error in tool_call handler {handler.__name__}: {e}",
                    exc_info=True
                )
                # Don't let handler errors block execution
                continue
        
        return None
    
    async def emit_tool_result(
        self, 
        event: ToolResultEvent
    ) -> ToolResultModification | None:
        """
        Emit tool_result event - aligned with coding-agent
        
        Handlers can modify tool results by returning ToolResultModification.
        First handler that returns a modification wins.
        
        Args:
            event: Tool result event
            
        Returns:
            ToolResultModification if result should be modified, None otherwise
        """
        handlers = self._handlers.get("tool_result", [])
        
        for handler in handlers:
            try:
                # Handle both sync and async handlers
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(event)
                else:
                    result = handler(event)
                
                # Check if handler wants to modify result
                if result and isinstance(result, ToolResultModification):
                    logger.debug(f"Tool result modified by extension: {event.tool_name}")
                    return result
                    
            except Exception as e:
                logger.error(
                    f"Error in tool_result handler {handler.__name__}: {e}",
                    exc_info=True
                )
                # Don't let handler errors break result flow
                continue
        
        return None


def wrap_tool_with_extensions(tool: Any, runner: ExtensionRunner) -> Any:
    """
    Wrap a tool with extension support - aligned with coding-agent wrapToolWithExtensions()
    
    The wrapped tool will:
    1. Emit tool_call event before execution (can block)
    2. Execute the tool
    3. Emit tool_result event after execution (can modify result)
    
    Args:
        tool: Tool to wrap (must have execute method)
        runner: Extension runner
        
    Returns:
        Wrapped tool with same interface
    """
    original_execute = tool.execute
    
    async def execute_with_extensions(
        tool_call_id: str,
        params: Dict[str, Any],
        signal: Any | None = None,
        on_update: Callable | None = None,
    ):
        """
        Execute tool with extension hooks
        
        Args:
            tool_call_id: Tool call ID
            params: Tool parameters
            signal: Abort signal
            on_update: Progress callback
            
        Returns:
            Tool result
            
        Raises:
            Exception: If tool_call is blocked or execution fails
        """
        # 1. Emit tool_call event (pre-execution)
        if runner.has_handlers("tool_call"):
            try:
                call_result = await runner.emit_tool_call(ToolCallEvent(
                    type="tool_call",
                    tool_name=tool.name,
                    tool_call_id=tool_call_id,
                    input=params
                ))
                
                # Check if blocked
                if call_result and call_result.block:
                    reason = call_result.reason or "Tool execution blocked by extension"
                    logger.warning(f"Tool {tool.name} blocked: {reason}")
                    raise Exception(reason)
                    
            except Exception as e:
                # Re-raise if it's our block exception
                if "blocked by extension" in str(e):
                    raise
                # Log and continue for other errors
                logger.error(f"Error in tool_call extension: {e}", exc_info=True)
        
        # 2. Execute tool
        try:
            # Handle both sync and async execute methods
            if asyncio.iscoroutinefunction(original_execute):
                result = await original_execute(tool_call_id, params, signal, on_update)
            else:
                result = original_execute(tool_call_id, params, signal, on_update)
            
            # 3. Emit tool_result event (post-execution, success)
            if runner.has_handlers("tool_result"):
                try:
                    # Convert result to expected format
                    content = result.content if hasattr(result, "content") else []
                    details = result.details if hasattr(result, "details") else None
                    
                    result_modification = await runner.emit_tool_result(ToolResultEvent(
                        type="tool_result",
                        tool_name=tool.name,
                        tool_call_id=tool_call_id,
                        input=params,
                        content=content if isinstance(content, list) else [{"type": "text", "text": str(content)}],
                        details=details,
                        is_error=False
                    ))
                    
                    # Apply modification if returned
                    if result_modification:
                        if result_modification.content is not None:
                            result.content = result_modification.content
                        if result_modification.details is not None:
                            result.details = result_modification.details
                            
                except Exception as e:
                    logger.error(f"Error in tool_result extension: {e}", exc_info=True)
            
            return result
            
        except Exception as err:
            # 4. Emit tool_result event (post-execution, error)
            if runner.has_handlers("tool_result"):
                try:
                    await runner.emit_tool_result(ToolResultEvent(
                        type="tool_result",
                        tool_name=tool.name,
                        tool_call_id=tool_call_id,
                        input=params,
                        content=[{"type": "text", "text": str(err)}],
                        details=None,
                        is_error=True
                    ))
                except Exception as e:
                    logger.error(f"Error in tool_result error extension: {e}", exc_info=True)
            
            # Re-raise original error
            raise
    
    # Create wrapped tool with same interface
    class WrappedTool:
        """Wrapped tool with extension support"""
        
        def __init__(self):
            self.name = tool.name
            self.description = tool.description
            self.get_schema = tool.get_schema
            self.execute = execute_with_extensions
            self._original = tool
    
    return WrappedTool()


def create_logging_extension() -> ExtensionRunner:
    """
    Create extension runner with logging handlers
    
    Useful for debugging tool execution.
    
    Returns:
        ExtensionRunner with logging handlers
    """
    runner = ExtensionRunner()
    
    def log_tool_call(event: ToolCallEvent) -> None:
        """Log tool calls"""
        logger.info(
            f"Tool call: {event.tool_name} "
            f"(id={event.tool_call_id}, params={event.input})"
        )
    
    def log_tool_result(event: ToolResultEvent) -> None:
        """Log tool results"""
        status = "error" if event.is_error else "success"
        logger.info(
            f"Tool result: {event.tool_name} "
            f"(id={event.tool_call_id}, status={status})"
        )
    
    runner.on("tool_call", log_tool_call)
    runner.on("tool_result", log_tool_result)
    
    return runner
