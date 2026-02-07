"""Format URL content for display."""

from __future__ import annotations

from .fetch import URLContent


def format_url_content(content: URLContent) -> str:
    """Format URL content for display.

    Args:
        content: URLContent to format

    Returns:
        Formatted string
    """
    if content.error:
        return f"[{content.url}] - Error: {content.error}"

    parts = [f"[{content.url}]"]

    if content.title:
        parts.append(f"Title: {content.title}")

    if content.description:
        parts.append(f"Description: {content.description}")

    if content.text:
        # Limit text length
        text = content.text[:500] + "..." if len(content.text) > 500 else content.text
        parts.append(f"Content: {text}")

    return "\n".join(parts)
