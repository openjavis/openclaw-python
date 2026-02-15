"""Telegram caption handling.

Telegram limits captions to 1024 characters. This module handles splitting
captions that exceed this limit.

Matches TypeScript src/telegram/caption.ts
"""

from __future__ import annotations

from typing import TypedDict, Optional

TELEGRAM_MAX_CAPTION_LENGTH = 1024


class CaptionSplitResult(TypedDict):
    """Result of splitting a caption."""

    caption: Optional[str]
    follow_up_text: Optional[str]


def split_telegram_caption(text: Optional[str]) -> CaptionSplitResult:
    """Split caption text if it exceeds Telegram's limit.

    If text is <= 1024 chars, returns it as caption.
    If text is > 1024 chars, returns None for caption and text as follow_up_text.

    Args:
        text: Caption text to split

    Returns:
        Dict with 'caption' and 'follow_up_text' keys
    """
    trimmed = (text or "").strip()

    if not trimmed:
        return {"caption": None, "follow_up_text": None}

    if len(trimmed) <= TELEGRAM_MAX_CAPTION_LENGTH:
        return {"caption": trimmed, "follow_up_text": None}

    # Caption too long, send all text as follow-up message
    return {"caption": None, "follow_up_text": trimmed}
