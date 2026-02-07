"""Apply link understanding to message context."""

from __future__ import annotations

from typing import Any

from .detect import detect_urls
from .fetch import fetch_url_content
from .format import format_url_content


async def apply_link_understanding(context: dict[str, Any], config: dict | None = None) -> None:
    """Apply link understanding to context.

    Automatically detects URLs in message and fetches content.

    Args:
        context: Message context
        config: Optional configuration
    """
    config = config or {}

    # Check if link understanding is enabled
    if not config.get("link_understanding_enabled", True):
        return

    # Get message text
    message_text = context.get("message", "")
    if not message_text:
        return

    # Detect URLs
    urls = detect_urls(message_text)
    if not urls:
        return

    # Fetch content for each URL
    contents = []
    for detected_url in urls:
        content = await fetch_url_content(detected_url.url)
        contents.append(content)

    # Format and add to context
    if contents:
        formatted = []
        for content in contents:
            formatted.append(format_url_content(content))

        context["link_understanding"] = {
            "urls": [c.url for c in contents],
            "contents": contents,
            "formatted": "\n\n".join(formatted),
        }
