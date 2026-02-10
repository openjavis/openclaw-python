"""Terminal hyperlinks"""
from __future__ import annotations

from pathlib import Path


def format_link(url: str, text: str | None = None) -> str:
    """
    Format clickable terminal link
    
    Args:
        url: URL to link to
        text: Display text (uses URL if None)
        
    Returns:
        Formatted link
    """
    if text is None:
        text = url
    
    # OSC 8 hyperlink format
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def format_file_link(path: Path | str, text: str | None = None) -> str:
    """
    Format clickable file link
    
    Args:
        path: File path
        text: Display text (uses path if None)
        
    Returns:
        Formatted link
    """
    path = Path(path).resolve()
    
    if text is None:
        text = str(path)
    
    # file:// URL
    url = f"file://{path}"
    
    return format_link(url, text)
