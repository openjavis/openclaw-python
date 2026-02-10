"""Markdown rendering"""
from __future__ import annotations


def render_markdown(text: str) -> str:
    """
    Render markdown to HTML
    
    Args:
        text: Markdown text
        
    Returns:
        HTML
    """
    from .parser import parse_markdown
    
    doc = parse_markdown(text)
    return doc.html


def render_to_terminal(text: str, width: int = 80) -> str:
    """
    Render markdown for terminal display
    
    Args:
        text: Markdown text
        width: Terminal width
        
    Returns:
        Formatted terminal text
    """
    # Simple terminal rendering
    # In full implementation, this would use rich or similar library
    
    lines = []
    in_code_block = False
    
    for line in text.split("\n"):
        # Code blocks
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        
        if in_code_block:
            lines.append(f"  {line}")
            continue
        
        # Headers
        if line.startswith("# "):
            lines.append(f"\n{'=' * width}")
            lines.append(line[2:].upper())
            lines.append(f"{'=' * width}\n")
        elif line.startswith("## "):
            lines.append(f"\n{line[3:]}")
            lines.append(f"{'-' * len(line[3:])}\n")
        elif line.startswith("### "):
            lines.append(f"\n{line[4:]}")
        
        # Lists
        elif line.startswith("- ") or line.startswith("* "):
            lines.append(f"  • {line[2:]}")
        elif line.strip() and line[0].isdigit() and ". " in line:
            lines.append(f"  {line}")
        
        # Regular text
        else:
            lines.append(line)
    
    return "\n".join(lines)
