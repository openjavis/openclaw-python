"""Agent tools"""

from .base import AgentTool, AgentToolBase, ToolResult
from .memory import MemoryGetTool, MemorySearchTool

# Import unified browser tool from new location
from openclaw.browser.tools.browser_tool import UnifiedBrowserTool

# Import new factory functions and utilities
from .bash import create_bash_tool
from .read import create_read_tool
from .write import create_write_tool
from .edit import create_edit_tool
from .truncate import (
    truncate_head,
    truncate_tail,
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    TruncationResult,
    format_size,
)
from .operations import (
    BashOperations,
    ReadOperations,
    WriteOperations,
    EditOperations,
)
from .default_operations import (
    DefaultBashOperations,
    DefaultReadOperations,
    DefaultWriteOperations,
    DefaultEditOperations,
)


def create_coding_tools(cwd: str, operations: dict | None = None) -> list[AgentToolBase]:
    """
    Create coding tools (read, bash, edit, write).
    
    Args:
        cwd: Current working directory
        operations: Optional dict of operation implementations
        
    Returns:
        List of configured tools
    """
    ops = operations or {}
    return [
        create_read_tool(cwd, ops.get("read")),
        create_bash_tool(cwd, ops.get("bash")),
        create_edit_tool(cwd, ops.get("edit")),
        create_write_tool(cwd, ops.get("write")),
    ]


def create_readonly_tools(cwd: str, operations: dict | None = None) -> list[AgentToolBase]:
    """
    Create read-only tools (read).
    
    Args:
        cwd: Current working directory
        operations: Optional dict of operation implementations
        
    Returns:
        List of configured tools
    """
    ops = operations or {}
    return [
        create_read_tool(cwd, ops.get("read")),
    ]


__all__ = [
    # Base classes
    "AgentTool",
    "AgentToolBase",
    "ToolResult",
    # Legacy tools
    "MemorySearchTool",
    "MemoryGetTool",
    "UnifiedBrowserTool",
    # Factory functions
    "create_bash_tool",
    "create_read_tool",
    "create_write_tool",
    "create_edit_tool",
    "create_coding_tools",
    "create_readonly_tools",
    # Utilities
    "truncate_head",
    "truncate_tail",
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
    "TruncationResult",
    "format_size",
    # Operations interfaces
    "BashOperations",
    "ReadOperations",
    "WriteOperations",
    "EditOperations",
    "DefaultBashOperations",
    "DefaultReadOperations",
    "DefaultWriteOperations",
    "DefaultEditOperations",
]

# Note: browser.py and browser_control.py are deprecated in favor of UnifiedBrowserTool
