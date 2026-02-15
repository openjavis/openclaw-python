"""
Bash execution tool matching pi-mono's bash.ts

This module provides bash command execution with:
- Output truncation (50KB/2000 lines)
- Streaming updates via on_update callback
- Cancellation support via signal
- Pluggable operations for remote execution

Matches pi-mono/packages/coding-agent/src/core/tools/bash.ts
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from typing import Any, Callable

from ..types import AgentToolResult, TextContent
from .base import AgentToolBase
from .default_operations import DefaultBashOperations
from .operations import BashOperations
from .truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    format_size,
    truncate_tail,
)

logger = logging.getLogger(__name__)


def create_bash_tool(
    cwd: str,
    operations: BashOperations | None = None,
    command_prefix: str | None = None,
) -> AgentToolBase:
    """
    Create a bash tool configured for a specific working directory.
    
    Args:
        cwd: Current working directory for commands
        operations: Bash operations implementation (defaults to local subprocess)
        command_prefix: Optional prefix to prepend to commands (e.g., "shopt -s expand_aliases")
        
    Returns:
        Configured BashTool instance
    """
    ops = operations or DefaultBashOperations()
    
    class BashTool(AgentToolBase[dict, dict]):
        """Bash command execution tool"""
        
        @property
        def name(self) -> str:
            return "bash"
        
        @property
        def label(self) -> str:
            return "Bash"
        
        @property
        def description(self) -> str:
            return (
                f"Execute a bash command in the current working directory. "
                f"Returns stdout and stderr. Output is truncated to last "
                f"{DEFAULT_MAX_LINES} lines or {DEFAULT_MAX_BYTES // 1024}KB "
                f"(whichever is hit first). If truncated, full output is saved "
                f"to a temp file. Optionally provide a timeout in seconds."
            )
        
        @property
        def parameters(self) -> dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (optional, no default timeout)"
                    }
                },
                "required": ["command"]
            }
        
        async def execute(
            self,
            tool_call_id: str,
            params: dict,
            signal: asyncio.Event | None = None,
            on_update: Callable[[AgentToolResult], None] | None = None,
        ) -> AgentToolResult[dict]:
            """Execute bash command with streaming and truncation"""
            
            command = params["command"]
            timeout = params.get("timeout")
            
            # Apply command prefix if configured
            resolved_command = f"{command_prefix}\n{command}" if command_prefix else command
            
            # Streaming output management
            # Keep a rolling buffer of the last chunk for tail truncation
            chunks: list[bytes] = []
            chunks_bytes = 0
            max_chunks_bytes = DEFAULT_MAX_BYTES * 2  # Keep more than we need
            
            # Temp file for full output
            temp_file_path: str | None = None
            temp_file: Any | None = None
            total_bytes = 0
            
            def handle_data(data: bytes):
                """Handle incoming data from subprocess"""
                nonlocal chunks_bytes, total_bytes, temp_file_path, temp_file
                
                total_bytes += len(data)
                
                # Start writing to temp file once we exceed threshold
                if total_bytes > DEFAULT_MAX_BYTES and not temp_file_path:
                    # Create temp file
                    fd, temp_file_path = tempfile.mkstemp(
                        prefix=f"openclaw-bash-{tool_call_id}-",
                        suffix=".log"
                    )
                    temp_file = open(fd, 'wb')
                    # Write all buffered chunks to the file
                    for chunk in chunks:
                        temp_file.write(chunk)
                
                # Write to temp file if we have one
                if temp_file:
                    temp_file.write(data)
                
                # Keep rolling buffer of recent data
                chunks.append(data)
                chunks_bytes += len(data)
                
                # Trim old chunks if buffer is too large
                while chunks_bytes > max_chunks_bytes and len(chunks) > 1:
                    removed = chunks.pop(0)
                    chunks_bytes -= len(removed)
                
                # Stream partial output to callback (truncated rolling buffer)
                if on_update:
                    full_buffer = b''.join(chunks)
                    full_text = full_buffer.decode('utf-8', errors='replace')
                    truncation = truncate_tail(full_text)
                    on_update(AgentToolResult(
                        content=[TextContent(text=truncation.content or "")],
                        details={
                            "truncation": truncation.__dict__ if truncation.truncated else None,
                            "full_output_path": temp_file_path,
                        }
                    ))
            
            # Check if already cancelled
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Execute command
            try:
                result = await ops.exec(
                    command=resolved_command,
                    cwd=cwd,
                    on_data=handle_data,
                    signal=signal,
                    timeout=timeout,
                )
            except asyncio.CancelledError:
                # Close temp file on cancellation
                if temp_file:
                    temp_file.close()
                
                # Combine all buffered chunks for output
                full_buffer = b''.join(chunks)
                output = full_buffer.decode('utf-8', errors='replace')
                
                if output:
                    output += "\n\n"
                output += "Command aborted"
                raise Exception(output)
            except asyncio.TimeoutError:
                # Close temp file on timeout
                if temp_file:
                    temp_file.close()
                
                # Combine all buffered chunks for output
                full_buffer = b''.join(chunks)
                output = full_buffer.decode('utf-8', errors='replace')
                
                if output:
                    output += "\n\n"
                output += f"Command timed out after {timeout} seconds"
                raise Exception(output)
            finally:
                # Always close temp file
                if temp_file:
                    temp_file.close()
            
            # Process final output
            full_buffer = b''.join(chunks)
            full_output = full_buffer.decode('utf-8', errors='replace')
            
            # Apply tail truncation
            truncation = truncate_tail(full_output)
            output_text = truncation.content or "(no output)"
            
            # Build details with truncation info
            details: dict[str, Any] | None = None
            
            if truncation.truncated:
                details = {
                    "truncation": truncation.__dict__,
                    "full_output_path": temp_file_path,
                }
                
                # Build actionable notice
                start_line = truncation.total_lines - truncation.output_lines + 1
                end_line = truncation.total_lines
                
                if truncation.last_line_partial:
                    # Edge case: last line alone > 50KB
                    last_line = full_output.split('\n')[-1]
                    last_line_size = format_size(len(last_line.encode('utf-8')))
                    output_text += (
                        f"\n\n[Showing last {format_size(truncation.output_bytes)} "
                        f"of line {end_line} (line is {last_line_size}). "
                        f"Full output: {temp_file_path}]"
                    )
                elif truncation.truncated_by == "lines":
                    output_text += (
                        f"\n\n[Showing lines {start_line}-{end_line} of "
                        f"{truncation.total_lines}. Full output: {temp_file_path}]"
                    )
                else:
                    output_text += (
                        f"\n\n[Showing lines {start_line}-{end_line} of "
                        f"{truncation.total_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). "
                        f"Full output: {temp_file_path}]"
                    )
            
            exit_code = result["exit_code"]
            if exit_code != 0 and exit_code is not None:
                output_text += f"\n\nCommand exited with code {exit_code}"
                raise Exception(output_text)
            
            return AgentToolResult(
                content=[TextContent(text=output_text)],
                details=details
            )
    
    return BashTool()


__all__ = ["create_bash_tool"]
