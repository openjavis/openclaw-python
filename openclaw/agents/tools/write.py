"""
File writing tool matching pi-mono's write.ts

This module provides file writing with:
- Automatic directory creation
- Overwrite existing files
- Cancellation support

Matches pi-mono/packages/coding-agent/src/core/tools/write.ts
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Callable

from ..types import AgentToolResult, TextContent
from .base import AgentToolBase
from .default_operations import DefaultWriteOperations
from .operations import WriteOperations
from .path_utils import resolve_to_cwd

logger = logging.getLogger(__name__)


def create_write_tool(
    cwd: str,
    operations: WriteOperations | None = None,
) -> AgentToolBase:
    """
    Create a write tool configured for a specific working directory.
    
    Args:
        cwd: Current working directory for relative paths
        operations: Write operations implementation (defaults to local filesystem)
        
    Returns:
        Configured WriteTool instance
    """
    ops = operations or DefaultWriteOperations()
    
    class WriteTool(AgentToolBase[dict, None]):
        """File writing tool"""
        
        @property
        def name(self) -> str:
            return "write"
        
        @property
        def label(self) -> str:
            return "Write File"
        
        @property
        def description(self) -> str:
            return (
                "Write content to a file. Creates the file if it doesn't exist, "
                "overwrites if it does. Automatically creates parent directories."
            )
        
        @property
        def parameters(self) -> dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to write to"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                },
                "required": ["path", "content"]
            }
        
        async def execute(
            self,
            tool_call_id: str,
            params: dict,
            signal: asyncio.Event | None = None,
            on_update: Callable[[AgentToolResult], None] | None = None,
        ) -> AgentToolResult[None]:
            """Write content to file"""
            
            path = params["path"]
            content = params["content"]
            
            # Resolve path
            absolute_path = resolve_to_cwd(path, cwd)
            dir_path = os.path.dirname(absolute_path)
            
            # Check if already cancelled
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Create parent directories if needed
            await ops.mkdir(dir_path)
            
            # Check if aborted before writing
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Write the file
            await ops.write_file(absolute_path, content)
            
            # Check if aborted after writing
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            return AgentToolResult(
                content=[
                    TextContent(
                        text=f"Successfully wrote {len(content)} bytes to {path}"
                    )
                ],
                details=None
            )
    
    return WriteTool()


__all__ = ["create_write_tool"]
