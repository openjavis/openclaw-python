"""Fetch URL content."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class URLContent:
    """Fetched URL content."""

    url: str
    title: str | None = None
    description: str | None = None
    text: str | None = None
    html: str | None = None
    error: str | None = None


async def fetch_url_content(
    url: str, timeout: int = 10, max_size: int = 1024 * 1024  # 1MB
) -> URLContent:
    """Fetch and parse URL content.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_size: Maximum content size in bytes

    Returns:
        URLContent with extracted information
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout, follow_redirects=True)

            response.raise_for_status()

            # Check size
            content = response.text
            if len(content) > max_size:
                return URLContent(url=url, error=f"Content too large ({len(content)} bytes)")

            # Extract title and description (basic HTML parsing)
            title = _extract_title(content)
            description = _extract_description(content)
            text = _extract_text(content)

            return URLContent(
                url=url, title=title, description=description, text=text, html=content
            )

    except Exception as e:
        return URLContent(url=url, error=str(e))


def _extract_title(html: str) -> str | None:
    """Extract title from HTML.

    Args:
        html: HTML content

    Returns:
        Title if found
    """
    import re

    # Try <title> tag
    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try og:title
    match = re.search(
        r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    return None


def _extract_description(html: str) -> str | None:
    """Extract description from HTML.

    Args:
        html: HTML content

    Returns:
        Description if found
    """
    import re

    # Try og:description
    match = re.search(
        r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    # Try meta description
    match = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    return None


def _extract_text(html: str) -> str | None:
    """Extract plain text from HTML.

    Args:
        html: HTML content

    Returns:
        Plain text
    """
    import re

    # Remove scripts and styles
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Clean up whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Limit length
    if len(text) > 1000:
        text = text[:1000] + "..."

    return text if text else None
