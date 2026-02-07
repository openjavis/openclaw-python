"""Telegram media upload."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MediaUploadResult:
    """Result of media upload."""

    file_id: str
    file_unique_id: str
    file_size: int | None = None
    mime_type: str | None = None


async def upload_media(
    bot_token: str,
    chat_id: int,
    media_path: Path | str,
    caption: str | None = None,
    media_type: str = "document",
) -> MediaUploadResult | None:
    """Upload media file to Telegram.

    Args:
        bot_token: Bot token
        chat_id: Chat ID
        media_path: Path to media file
        caption: Optional caption
        media_type: Media type (photo, document, audio, video)

    Returns:
        MediaUploadResult if successful
    """
    # In production, would upload file via Telegram API
    return MediaUploadResult(file_id="placeholder", file_unique_id="placeholder")
