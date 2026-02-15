"""
File reading tool matching pi-mono's read.ts

This module provides file reading with:
- Text file reading with pagination (offset/limit)
- Image reading with base64 encoding
- Output truncation (50KB/2000 lines)
- macOS path compatibility

Matches pi-mono/packages/coding-agent/src/core/tools/read.ts
"""
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any, Callable

from ..types import AgentToolResult, Content, ImageContent, TextContent
from .base import AgentToolBase
from .default_operations import DefaultReadOperations
from .operations import ReadOperations
from .path_utils import resolve_read_path
from .truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    format_size,
    truncate_head,
)

logger = logging.getLogger(__name__)


def create_read_tool(
    cwd: str,
    operations: ReadOperations | None = None,
    auto_resize_images: bool = True,
) -> AgentToolBase:
    """
    Create a read tool configured for a specific working directory.
    
    Args:
        cwd: Current working directory for relative paths
        operations: Read operations implementation (defaults to local filesystem)
        auto_resize_images: Whether to resize images (currently not implemented)
        
    Returns:
        Configured ReadTool instance
    """
    ops = operations or DefaultReadOperations()
    
    class ReadTool(AgentToolBase[dict, dict]):
        """File reading tool"""
        
        @property
        def name(self) -> str:
            return "read"
        
        @property
        def label(self) -> str:
            return "Read File"
        
        @property
        def description(self) -> str:
            return (
                f"Read the contents of a file. Supports text files and images "
                f"(jpg, png, gif, webp). Images are sent as attachments. "
                f"For text files, output is truncated to {DEFAULT_MAX_LINES} lines "
                f"or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first). "
                f"Use offset/limit for large files. When you need the full file, "
                f"continue with offset until complete."
            )
        
        @property
        def parameters(self) -> dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting line number (1-indexed, optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read (optional)"
                    },
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
            """Read file with pagination and image support"""
            
            path = params["path"]
            offset = params.get("offset")
            limit = params.get("limit")
            
            # Resolve path with macOS compatibility
            absolute_path = resolve_read_path(path, cwd)
            
            # Check if already cancelled
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Check if file exists
            await ops.access(absolute_path)
            
            # Check if aborted after access check
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Detect if image
            mime_type = await ops.detect_image_mime_type(absolute_path)
            
            if mime_type:
                # Read as image (binary)
                buffer = await ops.read_file(absolute_path)
                base64_data = base64.b64encode(buffer).decode('utf-8')
                
                # Check if aborted after reading
                if signal and signal.is_set():
                    raise asyncio.CancelledError("Operation aborted")
                
                # TODO: Implement image resizing if auto_resize_images is True
                # For now, just return the image as-is
                text_note = f"Read image file [{mime_type}]"
                
                return AgentToolResult(
                    content=[
                        TextContent(text=text_note),
                        ImageContent(data=base64_data, mime_type=mime_type),
                    ],
                    details=None
                )
            else:
                # Read as text file
                buffer = await ops.read_file(absolute_path)
                text_content = buffer.decode('utf-8')
                all_lines = text_content.split('\n')
                total_file_lines = len(all_lines)
                
                # Check if aborted after reading
                if signal and signal.is_set():
                    raise asyncio.CancelledError("Operation aborted")
                
                # Apply offset (1-indexed to 0-indexed)
                start_line = max(0, (offset - 1)) if offset else 0
                start_line_display = start_line + 1  # For display (1-indexed)
                
                # Check if offset is out of bounds
                if start_line >= total_file_lines:
                    raise ValueError(
                        f"Offset {offset} is beyond end of file "
                        f"({total_file_lines} lines total)"
                    )
                
                # Apply limit if specified
                user_limited_lines: int | None = None
                if limit is not None:
                    end_line = min(start_line + limit, total_file_lines)
                    selected_content = '\n'.join(all_lines[start_line:end_line])
                    user_limited_lines = end_line - start_line
                else:
                    selected_content = '\n'.join(all_lines[start_line:])
                
                # Apply truncation (respects both line and byte limits)
                truncation = truncate_head(selected_content)
                
                output_text: str
                details: dict[str, Any] | None = None
                
                if truncation.first_line_exceeds_limit:
                    # First line at offset exceeds 50KB - tell model to use bash
                    first_line_size = format_size(
                        len(all_lines[start_line].encode('utf-8'))
                    )
                    output_text = (
                        f"[Line {start_line_display} is {first_line_size}, exceeds "
                        f"{format_size(DEFAULT_MAX_BYTES)} limit. Use bash: "
                        f"sed -n '{start_line_display}p' {path} | "
                        f"head -c {DEFAULT_MAX_BYTES}]"
                    )
                    details = {"truncation": truncation.__dict__}
                elif truncation.truncated:
                    # Truncation occurred - build actionable notice
                    end_line_display = start_line_display + truncation.output_lines - 1
                    next_offset = end_line_display + 1
                    
                    output_text = truncation.content
                    
                    if truncation.truncated_by == "lines":
                        output_text += (
                            f"\n\n[Showing lines {start_line_display}-{end_line_display} "
                            f"of {total_file_lines}. Use offset={next_offset} to continue.]"
                        )
                    else:
                        output_text += (
                            f"\n\n[Showing lines {start_line_display}-{end_line_display} "
                            f"of {total_file_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). "
                            f"Use offset={next_offset} to continue.]"
                        )
                    
                    details = {"truncation": truncation.__dict__}
                elif user_limited_lines is not None and start_line + user_limited_lines < total_file_lines:
                    # User specified limit, there's more content, but no truncation
                    remaining = total_file_lines - (start_line + user_limited_lines)
                    next_offset = start_line + user_limited_lines + 1
                    
                    output_text = truncation.content
                    output_text += (
                        f"\n\n[{remaining} more lines in file. "
                        f"Use offset={next_offset} to continue.]"
                    )
                else:
                    # No truncation, no user limit exceeded
                    output_text = truncation.content
                
                return AgentToolResult(
                    content=[TextContent(text=output_text)],
                    details=details
                )
    
    return ReadTool()


__all__ = ["create_read_tool"]
