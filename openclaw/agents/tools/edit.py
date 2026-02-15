"""
File editing tool matching pi-mono's edit.ts

This module provides file editing with:
- Exact text replacement
- Fuzzy matching for Unicode and whitespace variations
- Uniqueness checking
- Diff generation
- Line ending preservation

Matches pi-mono/packages/coding-agent/src/core/tools/edit.ts
"""
from __future__ import annotations

import asyncio
import difflib
import logging
from typing import Any, Callable

from ..types import AgentToolResult, TextContent
from .base import AgentToolBase
from .default_operations import DefaultEditOperations
from .operations import EditOperations
from .path_utils import resolve_to_cwd

logger = logging.getLogger(__name__)


def create_edit_tool(
    cwd: str,
    operations: EditOperations | None = None,
) -> AgentToolBase:
    """
    Create an edit tool configured for a specific working directory.
    
    Args:
        cwd: Current working directory for relative paths
        operations: Edit operations implementation (defaults to local filesystem)
        
    Returns:
        Configured EditTool instance
    """
    ops = operations or DefaultEditOperations()
    
    class EditTool(AgentToolBase[dict, dict]):
        """File editing tool"""
        
        @property
        def name(self) -> str:
            return "edit"
        
        @property
        def label(self) -> str:
            return "Edit File"
        
        @property
        def description(self) -> str:
            return (
                "Edit a file by replacing exact text. The oldText must match exactly "
                "(including whitespace). Use this for precise, surgical edits."
            )
        
        @property
        def parameters(self) -> dict[str, Any]:
            return {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to edit"
                    },
                    "oldText": {
                        "type": "string",
                        "description": "Exact text to replace (must match including whitespace)"
                    },
                    "newText": {
                        "type": "string",
                        "description": "New text to replace with"
                    },
                },
                "required": ["path", "oldText", "newText"]
            }
        
        async def execute(
            self,
            tool_call_id: str,
            params: dict,
            signal: asyncio.Event | None = None,
            on_update: Callable[[AgentToolResult], None] | None = None,
        ) -> AgentToolResult[dict]:
            """Edit file by replacing text"""
            
            path = params["path"]
            old_text = params["oldText"]
            new_text = params["newText"]
            
            # Resolve path
            absolute_path = resolve_to_cwd(path, cwd)
            
            # Check if already cancelled
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Check if file exists
            try:
                await ops.access(absolute_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found: {path}")
            
            # Check if aborted before reading
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Read the file
            buffer = await ops.read_file(absolute_path)
            raw_content = buffer.decode('utf-8')
            
            # Check if aborted after reading
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Strip BOM before matching (LLM won't include invisible BOM in oldText)
            bom = ""
            content = raw_content
            if raw_content.startswith('\ufeff'):
                bom = '\ufeff'
                content = raw_content[1:]
            
            # Detect line ending
            original_ending = detect_line_ending(content)
            
            # Normalize to LF for matching
            normalized_content = normalize_to_lf(content)
            normalized_old_text = normalize_to_lf(old_text)
            normalized_new_text = normalize_to_lf(new_text)
            
            # Find the old text using fuzzy matching
            match_result = fuzzy_find_text(normalized_content, normalized_old_text)
            
            if not match_result["found"]:
                raise ValueError(
                    f"Could not find the exact text in {path}. "
                    f"The old text must match exactly including all whitespace and newlines."
                )
            
            # Count occurrences using fuzzy-normalized content for consistency
            fuzzy_content = normalize_for_fuzzy_match(normalized_content)
            fuzzy_old_text = normalize_for_fuzzy_match(normalized_old_text)
            occurrences = fuzzy_content.count(fuzzy_old_text)
            
            if occurrences > 1:
                raise ValueError(
                    f"Found {occurrences} occurrences of the text in {path}. "
                    f"The text must be unique. Please provide more context to make it unique."
                )
            
            # Check if aborted before writing
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Perform replacement using the matched text position
            base_content = match_result["content_for_replacement"]
            index = match_result["index"]
            match_length = match_result["match_length"]
            
            new_content = (
                base_content[:index] +
                normalized_new_text +
                base_content[index + match_length:]
            )
            
            # Verify the replacement actually changed something
            if base_content == new_content:
                raise ValueError(
                    f"No changes made to {path}. The replacement produced identical content. "
                    f"This might indicate an issue with special characters or the text "
                    f"not existing as expected."
                )
            
            # Restore line endings and BOM
            final_content = bom + restore_line_endings(new_content, original_ending)
            
            # Write the file
            await ops.write_file(absolute_path, final_content)
            
            # Check if aborted after writing
            if signal and signal.is_set():
                raise asyncio.CancelledError("Operation aborted")
            
            # Generate diff
            diff_result = generate_diff_string(base_content, new_content)
            
            return AgentToolResult(
                content=[
                    TextContent(text=f"Successfully replaced text in {path}.")
                ],
                details={
                    "diff": diff_result["diff"],
                    "first_changed_line": diff_result["first_changed_line"],
                }
            )
    
    return EditTool()


def detect_line_ending(text: str) -> str:
    """Detect line ending style (CRLF or LF)"""
    if '\r\n' in text:
        return '\r\n'
    return '\n'


def normalize_to_lf(text: str) -> str:
    """Normalize line endings to LF"""
    return text.replace('\r\n', '\n')


def restore_line_endings(text: str, ending: str) -> str:
    """Restore original line endings"""
    if ending == '\r\n':
        return text.replace('\n', '\r\n')
    return text


def normalize_for_fuzzy_match(text: str) -> str:
    """
    Normalize text for fuzzy matching.
    
    Handles:
    - Trailing whitespace per line
    - Smart quotes → straight quotes
    - Various dashes → hyphen
    - Special spaces → regular space
    """
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Smart single quotes → '
    text = text.translate(str.maketrans({
        '\u2018': "'",  # Left single quotation mark
        '\u2019': "'",  # Right single quotation mark
        '\u201a': "'",  # Single low-9 quotation mark
        '\u201b': "'",  # Single high-reversed-9 quotation mark
    }))
    
    # Smart double quotes → "
    text = text.translate(str.maketrans({
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u201e': '"',  # Double low-9 quotation mark
        '\u201f': '"',  # Double high-reversed-9 quotation mark
    }))
    
    # Various dashes/hyphens → -
    text = text.translate(str.maketrans({
        '\u2010': '-',  # Hyphen
        '\u2011': '-',  # Non-breaking hyphen
        '\u2012': '-',  # Figure dash
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2015': '-',  # Horizontal bar
        '\u2212': '-',  # Minus sign
    }))
    
    # Special spaces → regular space
    text = text.translate(str.maketrans({
        '\u00a0': ' ',  # Non-breaking space
        '\u2002': ' ',  # En space
        '\u2003': ' ',  # Em space
        '\u2004': ' ',  # Three-per-em space
        '\u2005': ' ',  # Four-per-em space
        '\u2006': ' ',  # Six-per-em space
        '\u2007': ' ',  # Figure space
        '\u2008': ' ',  # Punctuation space
        '\u2009': ' ',  # Thin space
        '\u200a': ' ',  # Hair space
        '\u202f': ' ',  # Narrow no-break space
        '\u205f': ' ',  # Medium mathematical space
        '\u3000': ' ',  # Ideographic space
    }))
    
    return text


def fuzzy_find_text(content: str, search_text: str) -> dict[str, Any]:
    """
    Find text using fuzzy matching.
    
    Tries exact match first, then fuzzy match if exact fails.
    
    Returns:
        Dict with:
        - found: bool
        - index: int (position in content_for_replacement)
        - match_length: int
        - content_for_replacement: str (normalized content used for replacement)
    """
    # Try exact match first
    if search_text in content:
        return {
            "found": True,
            "index": content.index(search_text),
            "match_length": len(search_text),
            "content_for_replacement": content,
        }
    
    # Try fuzzy match
    fuzzy_content = normalize_for_fuzzy_match(content)
    fuzzy_search = normalize_for_fuzzy_match(search_text)
    
    if fuzzy_search in fuzzy_content:
        return {
            "found": True,
            "index": fuzzy_content.index(fuzzy_search),
            "match_length": len(fuzzy_search),
            "content_for_replacement": fuzzy_content,
        }
    
    return {
        "found": False,
        "index": -1,
        "match_length": 0,
        "content_for_replacement": content,
    }


def generate_diff_string(old_content: str, new_content: str) -> dict[str, Any]:
    """
    Generate unified diff string.
    
    Returns:
        Dict with:
        - diff: str (unified diff)
        - first_changed_line: int (1-indexed line number of first change)
    """
    old_lines = old_content.split('\n')
    new_lines = new_content.split('\n')
    
    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        old_lines,
        new_lines,
        lineterm='',
        n=3,  # Context lines
    ))
    
    # Find first changed line
    first_changed_line = 1
    for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines), 1):
        if old_line != new_line:
            first_changed_line = i
            break
    
    return {
        "diff": '\n'.join(diff_lines),
        "first_changed_line": first_changed_line,
    }


__all__ = ["create_edit_tool"]
