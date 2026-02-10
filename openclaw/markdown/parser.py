"""Markdown parser"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarkdownDocument:
    """Parsed markdown document"""
    
    raw_text: str
    html: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    headings: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    code_blocks: list[dict[str, Any]] = field(default_factory=list)


def parse_markdown(text: str, extensions: list[str] | None = None) -> MarkdownDocument:
    """
    Parse markdown text
    
    Args:
        text: Markdown text
        extensions: Optional markdown extensions
        
    Returns:
        Parsed document
    """
    try:
        import markdown
    except ImportError:
        # Fallback if markdown not installed
        return MarkdownDocument(
            raw_text=text,
            html=text,  # No conversion
        )
    
    # Configure extensions
    if extensions is None:
        extensions = [
            "fenced_code",
            "tables",
            "toc",
            "codehilite",
        ]
    
    # Create markdown instance
    md = markdown.Markdown(extensions=extensions)
    
    # Convert
    html = md.convert(text)
    
    # Extract metadata (frontmatter)
    metadata = {}
    if hasattr(md, "Meta"):
        metadata = dict(md.Meta)
    
    # Extract headings
    headings = []
    if hasattr(md, "toc_tokens"):
        for token in md.toc_tokens:
            headings.append({
                "level": token.get("level"),
                "text": token.get("name"),
                "id": token.get("id"),
            })
    
    return MarkdownDocument(
        raw_text=text,
        html=html,
        metadata=metadata,
        headings=headings,
    )
