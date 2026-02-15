"""
Output truncation utilities matching pi-mono's truncate.ts

This module provides truncation algorithms for tool outputs:
- truncate_head: Truncate from beginning (for file reads)
- truncate_tail: Truncate from end (for bash outputs)
- UTF-8 safe byte counting
- Dual limits (lines + bytes)

Matches pi-mono/packages/coding-agent/src/core/tools/truncate.ts
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Default limits matching pi-mono
DEFAULT_MAX_LINES = 2000
DEFAULT_MAX_BYTES = 50 * 1024  # 50KB
GREP_MAX_LINE_LENGTH = 500  # Max chars per grep match line


@dataclass
class TruncationResult:
    """Result of truncation operation"""
    
    content: str
    """The truncated content"""
    
    truncated: bool
    """Whether truncation occurred"""
    
    truncated_by: Literal["lines", "bytes"] | None
    """What caused truncation (lines or bytes limit)"""
    
    total_lines: int
    """Total number of lines in original content"""
    
    total_bytes: int
    """Total bytes in original content"""
    
    output_lines: int
    """Number of lines in output"""
    
    output_bytes: int
    """Number of bytes in output"""
    
    last_line_partial: bool
    """Whether last line was partially truncated (tail only)"""
    
    first_line_exceeds_limit: bool
    """Whether first line alone exceeds byte limit (head only)"""
    
    max_lines: int
    """Maximum lines limit used"""
    
    max_bytes: int
    """Maximum bytes limit used"""


@dataclass
class TruncationOptions:
    """Options for truncation"""
    
    max_lines: int | None = None
    max_bytes: int | None = None


def truncate_head(
    content: str,
    options: TruncationOptions | None = None
) -> TruncationResult:
    """
    Truncate content from the beginning (keep head).
    
    Used for file reads - shows the first N lines/bytes.
    
    Algorithm:
    1. Check if no truncation needed
    2. Check if first line alone exceeds byte limit
    3. Collect complete lines that fit within both limits
    
    Args:
        content: Content to truncate
        options: Truncation options (defaults to DEFAULT_MAX_LINES/BYTES)
        
    Returns:
        TruncationResult with truncated content and metadata
    """
    if options is None:
        options = TruncationOptions()
    
    max_lines = options.max_lines if options.max_lines is not None else DEFAULT_MAX_LINES
    max_bytes = options.max_bytes if options.max_bytes is not None else DEFAULT_MAX_BYTES
    
    total_bytes = len(content.encode('utf-8'))
    lines = content.split('\n')
    total_lines = len(lines)
    
    # Check if no truncation needed
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=total_lines,
            output_bytes=total_bytes,
            last_line_partial=False,
            first_line_exceeds_limit=False,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )
    
    # Check if first line alone exceeds byte limit
    first_line_bytes = len(lines[0].encode('utf-8'))
    if first_line_bytes > max_bytes:
        return TruncationResult(
            content="",
            truncated=True,
            truncated_by="bytes",
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=0,
            output_bytes=0,
            last_line_partial=False,
            first_line_exceeds_limit=True,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )
    
    # Collect complete lines that fit
    output_lines_arr: list[str] = []
    output_bytes_count = 0
    truncated_by: Literal["lines", "bytes"] = "lines"
    
    for i, line in enumerate(lines):
        if i >= max_lines:
            truncated_by = "lines"
            break
        
        # +1 for newline (except first line)
        line_bytes = len(line.encode('utf-8')) + (1 if i > 0 else 0)
        
        if output_bytes_count + line_bytes > max_bytes:
            truncated_by = "bytes"
            break
        
        output_lines_arr.append(line)
        output_bytes_count += line_bytes
    
    # If we exited due to line limit
    if len(output_lines_arr) >= max_lines and output_bytes_count <= max_bytes:
        truncated_by = "lines"
    
    output_content = '\n'.join(output_lines_arr)
    final_output_bytes = len(output_content.encode('utf-8'))
    
    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines_arr),
        output_bytes=final_output_bytes,
        last_line_partial=False,
        first_line_exceeds_limit=False,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def truncate_tail(
    content: str,
    options: TruncationOptions | None = None
) -> TruncationResult:
    """
    Truncate content from the end (keep tail).
    
    Used for bash outputs - shows the last N lines/bytes.
    
    Algorithm:
    1. Check if no truncation needed
    2. Work backwards from the end, collecting lines
    3. If single line exceeds limit, truncate that line from end
    
    Args:
        content: Content to truncate
        options: Truncation options (defaults to DEFAULT_MAX_LINES/BYTES)
        
    Returns:
        TruncationResult with truncated content and metadata
    """
    if options is None:
        options = TruncationOptions()
    
    max_lines = options.max_lines if options.max_lines is not None else DEFAULT_MAX_LINES
    max_bytes = options.max_bytes if options.max_bytes is not None else DEFAULT_MAX_BYTES
    
    total_bytes = len(content.encode('utf-8'))
    lines = content.split('\n')
    total_lines = len(lines)
    
    # Check if no truncation needed
    if total_lines <= max_lines and total_bytes <= max_bytes:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=total_lines,
            output_bytes=total_bytes,
            last_line_partial=False,
            first_line_exceeds_limit=False,
            max_lines=max_lines,
            max_bytes=max_bytes,
        )
    
    # Work backwards from the end
    output_lines_arr: list[str] = []
    output_bytes_count = 0
    truncated_by: Literal["lines", "bytes"] = "lines"
    last_line_partial = False
    
    for i in range(len(lines) - 1, -1, -1):
        if len(output_lines_arr) >= max_lines:
            truncated_by = "lines"
            break
        
        line = lines[i]
        # +1 for newline (except for lines we've already added)
        line_bytes = len(line.encode('utf-8')) + (1 if output_lines_arr else 0)
        
        if output_bytes_count + line_bytes > max_bytes:
            truncated_by = "bytes"
            # Edge case: if we haven't added ANY lines yet and this line exceeds maxBytes,
            # take the end of the line (partial)
            if not output_lines_arr:
                truncated_line = truncate_string_to_bytes_from_end(line, max_bytes)
                output_lines_arr.insert(0, truncated_line)
                output_bytes_count = len(truncated_line.encode('utf-8'))
                last_line_partial = True
            break
        
        output_lines_arr.insert(0, line)
        output_bytes_count += line_bytes
    
    # If we exited due to line limit
    if len(output_lines_arr) >= max_lines and output_bytes_count <= max_bytes:
        truncated_by = "lines"
    
    output_content = '\n'.join(output_lines_arr)
    final_output_bytes = len(output_content.encode('utf-8'))
    
    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines_arr),
        output_bytes=final_output_bytes,
        last_line_partial=last_line_partial,
        first_line_exceeds_limit=False,
        max_lines=max_lines,
        max_bytes=max_bytes,
    )


def truncate_string_to_bytes_from_end(text: str, max_bytes: int) -> str:
    """
    Truncate string to max bytes from the end (UTF-8 safe).
    
    Takes the last N bytes of a string, ensuring we don't break
    UTF-8 multibyte characters.
    
    Args:
        text: Text to truncate
        max_bytes: Maximum bytes to keep
        
    Returns:
        Truncated string (from end)
    """
    encoded = text.encode('utf-8')
    
    if len(encoded) <= max_bytes:
        return text
    
    # Take the last max_bytes
    truncated_bytes = encoded[-max_bytes:]
    
    # Decode, ignoring any broken characters at the start
    # (which might happen if we cut in the middle of a multibyte char)
    try:
        return truncated_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # If we have broken chars at start, try removing bytes until valid
        for i in range(1, min(4, len(truncated_bytes))):
            try:
                return truncated_bytes[i:].decode('utf-8')
            except UnicodeDecodeError:
                continue
        
        # Fallback: use replace to handle broken chars
        return truncated_bytes.decode('utf-8', errors='replace')


def format_size(num_bytes: int) -> str:
    """
    Format byte count as human-readable size.
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5KB", "2.3MB")
    """
    if num_bytes < 1024:
        return f"{num_bytes}B"
    elif num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f}KB"
    else:
        return f"{num_bytes / (1024 * 1024):.1f}MB"


__all__ = [
    "DEFAULT_MAX_LINES",
    "DEFAULT_MAX_BYTES",
    "GREP_MAX_LINE_LENGTH",
    "TruncationResult",
    "TruncationOptions",
    "truncate_head",
    "truncate_tail",
    "truncate_string_to_bytes_from_end",
    "format_size",
]
