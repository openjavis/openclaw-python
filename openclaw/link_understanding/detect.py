"""URL detection in text."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DetectedURL:
    """A detected URL in text."""

    url: str
    start: int
    end: int
    display_text: str | None = None


def detect_urls(text: str) -> list[DetectedURL]:
    """Detect URLs in text.

    Args:
        text: Text to search for URLs

    Returns:
        List of detected URLs
    """
    if not text:
        return []

    # URL pattern
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

    urls: list[DetectedURL] = []

    for match in re.finditer(url_pattern, text):
        urls.append(DetectedURL(url=match.group(0), start=match.start(), end=match.end()))

    return urls


def has_urls(text: str) -> bool:
    """Check if text contains URLs.

    Args:
        text: Text to check

    Returns:
        True if URLs found
    """
    return len(detect_urls(text)) > 0
