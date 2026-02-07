"""Media parsing from agent output.

Extracts media URLs and directives from agent text output.
Aligned with TypeScript src/media/parse.ts
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MediaParseResult:
    """Result of parsing media from output text."""

    text: str | None = None
    media_url: str | None = None
    media_urls: list[str] | None = None
    audio_as_voice: bool = False


def split_media_from_output(text: str) -> MediaParseResult:
    """Split media URLs and directives from output text.

    Extracts:
    - [[image:URL]] - Image URL
    - [[audio:URL]] - Audio URL
    - [[video:URL]] - Video URL
    - [[audio_as_voice]] - Audio as voice directive
    - Multiple media URLs

    Args:
        text: Output text from agent

    Returns:
        MediaParseResult with separated text and media
    """
    if not text:
        return MediaParseResult()

    media_urls: list[str] = []
    audio_as_voice = False
    clean_text = text

    # Pattern for media directives: [[TYPE:URL]]
    media_pattern = r"\[\[(image|audio|video|file):([^\]]+)\]\]"

    def replace_media(match: re.Match) -> str:
        nonlocal audio_as_voice
        media_type = match.group(1)
        url = match.group(2).strip()

        if url:
            media_urls.append(url)

        return ""

    clean_text = re.sub(media_pattern, replace_media, clean_text, flags=re.IGNORECASE)

    # Check for audio_as_voice directive
    voice_pattern = r"\[\[audio_as_voice\]\]"
    if re.search(voice_pattern, clean_text, re.IGNORECASE):
        audio_as_voice = True
        clean_text = re.sub(voice_pattern, "", clean_text, flags=re.IGNORECASE)

    # Clean up extra whitespace
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    return MediaParseResult(
        text=clean_text if clean_text else None,
        media_url=media_urls[0] if len(media_urls) == 1 else None,
        media_urls=media_urls if len(media_urls) > 1 else None,
        audio_as_voice=audio_as_voice,
    )
