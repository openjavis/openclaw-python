"""Code fence extraction"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class CodeBlock:
    """Extracted code block"""
    
    language: str
    code: str
    start_line: int
    end_line: int
    metadata: dict[str, str] | None = None


def extract_code_blocks(text: str) -> list[CodeBlock]:
    """
    Extract code blocks from markdown
    
    Args:
        text: Markdown text
        
    Returns:
        List of code blocks
    """
    blocks = []
    
    # Pattern for fenced code blocks
    pattern = r"```(\w+)?\n(.*?)```"
    
    for match in re.finditer(pattern, text, re.DOTALL):
        language = match.group(1) or "text"
        code = match.group(2).rstrip()
        
        # Calculate line numbers
        start_pos = match.start()
        start_line = text[:start_pos].count("\n") + 1
        end_line = start_line + code.count("\n")
        
        blocks.append(CodeBlock(
            language=language,
            code=code,
            start_line=start_line,
            end_line=end_line,
        ))
    
    return blocks
