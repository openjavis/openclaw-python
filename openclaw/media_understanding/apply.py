"""Apply media understanding to message context."""

from __future__ import annotations

from typing import Any

from .runner import run_media_understanding
from .types import MediaScope


async def apply_media_understanding(
    context: dict[str, Any], config: dict | None = None, scope: MediaScope = MediaScope.AUTO
) -> None:
    """Apply media understanding to context.

    Automatically processes media in the context and adds
    descriptions/transcripts.

    Args:
        context: Message context with media
        config: Optional configuration
        scope: Processing scope
    """
    config = config or {}

    # Extract media from context
    media_items = context.get("media", [])
    if not media_items:
        return

    # Process each media item
    results = []
    for item in media_items:
        media_url = item.get("url")
        media_type = item.get("type", "image")

        if not media_url:
            continue

        result = await run_media_understanding(
            media_url=media_url, media_type=media_type, scope=scope, config=config
        )

        if result:
            results.append(result)

    # Add results to context
    if results:
        context["media_understanding"] = [
            {
                "url": r.url,
                "type": r.media_type,
                "description": r.description,
                "transcript": r.transcript,
                "provider": r.provider,
            }
            for r in results
        ]
