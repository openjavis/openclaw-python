"""Message formatting for Telegram - aligned with TypeScript format.ts"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


def escape_html(text: str) -> str:
    """Escape HTML special characters for safe use in Telegram HTML messages."""
    if not text:
        return text
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def escape_html_attr(text: str) -> str:
    """Escape HTML special characters for use in HTML attribute values."""
    text = escape_html(text)
    text = text.replace('"', "&quot;")
    return text


@dataclass
class TelegramChunk:
    """A single formatted chunk ready to send to Telegram."""
    html: str
    plain: str
    length: int


def markdown_to_telegram_chunks(
    text: str,
    limit: int = 4096,
) -> List["TelegramChunk"]:
    """
    Convert Markdown text to a list of Telegram-ready HTML chunks.

    Each chunk fits within *limit* characters of the HTML output.

    Args:
        text: Markdown input text.
        limit: Maximum characters per chunk (Telegram limit = 4096).

    Returns:
        List of TelegramChunk objects.
    """
    html = markdown_to_html(text)
    raw_chunks = chunk_message(html, max_length=limit)
    return [
        TelegramChunk(html=c, plain=re.sub(r"<[^>]+>", "", c), length=len(c))
        for c in raw_chunks
    ]


def markdown_to_html(text: str) -> str:
    """Convert Markdown to Telegram HTML
    
    Telegram supports: <b>, <i>, <u>, <s>, <code>, <pre>, <a href="">
    """
    if not text:
        return text
    
    # Escape HTML entities first
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # Italic: *text* or _text_
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    
    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Code blocks: ```code```
    text = re.sub(
        r'```(?:\w+\n)?(.+?)```',
        r'<pre><code>\1</code></pre>',
        text,
        flags=re.DOTALL
    )
    
    # Links: [text](url)
    text = re.sub(
        r'\[([^\]]+)\]\(([^\)]+)\)',
        r'<a href="\2">\1</a>',
        text
    )
    
    return text


def chunk_message(text: str, max_length: int = 4096) -> List[str]:
    """Split long messages into chunks
    
    Telegram has a 4096 character limit per message.
    Split at paragraph boundaries when possible.
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs
    paragraphs = text.split("\n\n")
    
    for paragraph in paragraphs:
        # If adding this paragraph exceeds limit
        if len(current_chunk) + len(paragraph) + 2 > max_length:
            # If current chunk has content, save it
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            # If paragraph itself is too long, split by lines
            if len(paragraph) > max_length:
                lines = paragraph.split("\n")
                for line in lines:
                    if len(current_chunk) + len(line) + 1 > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""
                    current_chunk += line + "\n"
            else:
                current_chunk = paragraph + "\n\n"
        else:
            current_chunk += paragraph + "\n\n"
    
    # Add remaining chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def format_code_block(code: str, language: str = "") -> str:
    """Format code block for Telegram"""
    return f"<pre><code class='{language}'>{code}</code></pre>"


def format_table(rows: List[List[str]]) -> str:
    """Format table for Telegram (as monospace text)"""
    if not rows:
        return ""
    
    # Calculate column widths
    col_widths = [max(len(str(cell)) for cell in col) for col in zip(*rows)]
    
    # Build table
    lines = []
    for row in rows:
        cells = [str(cell).ljust(width) for cell, width in zip(row, col_widths)]
        lines.append(" | ".join(cells))
    
    return "<pre>" + "\n".join(lines) + "</pre>"


__all__ = [
    "markdown_to_html",
    "chunk_message",
    "format_code_block",
    "format_table",
]
