"""
Telegram media handling

Downloads and processes media from Telegram messages.
Matches TypeScript Telegram/WhatsApp media handling patterns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from telegram import File, Message, PhotoSize

from openclaw.media.loader import MediaResult, load_media
from openclaw.media.mime import MediaKind, detect_mime, extension_for_mime

logger = logging.getLogger(__name__)


@dataclass
class TelegramMediaInfo:
    """Telegram media information."""
    media_type: str  # photo, document, video, audio, sticker
    file_id: str
    file_name: str | None
    mime_type: str | None
    file_size: int | None


class TelegramMediaHandler:
    """
    Handles Telegram media downloads and processing.
    
    Features:
    - Download photos, documents, videos, audio, stickers
    - Save to workspace
    - MIME type detection
    - Size limits
    """
    
    def __init__(self, workspace_root: Path | None = None, max_bytes: int | None = None):
        """
        Initialize Telegram media handler.
        
        Args:
            workspace_root: Workspace root for saving media
            max_bytes: Maximum file size
        """
        self.workspace_root = workspace_root
        self.max_bytes = max_bytes
        
        if workspace_root:
            self.media_dir = workspace_root / "media" / "inbound"
            self.media_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.media_dir = None
    
    def extract_media_info(self, message: Message) -> TelegramMediaInfo | None:
        """
        Extract media info from Telegram message.
        
        Args:
            message: Telegram message
        
        Returns:
            TelegramMediaInfo or None if no media
        """
        # Photo
        if message.photo:
            # Get largest photo
            photo: PhotoSize = max(message.photo, key=lambda p: p.file_size or 0)
            return TelegramMediaInfo(
                media_type="photo",
                file_id=photo.file_id,
                file_name=None,
                mime_type="image/jpeg",
                file_size=photo.file_size,
            )
        
        # Document
        if message.document:
            return TelegramMediaInfo(
                media_type="document",
                file_id=message.document.file_id,
                file_name=message.document.file_name,
                mime_type=message.document.mime_type,
                file_size=message.document.file_size,
            )
        
        # Video
        if message.video:
            return TelegramMediaInfo(
                media_type="video",
                file_id=message.video.file_id,
                file_name=message.video.file_name,
                mime_type=message.video.mime_type,
                file_size=message.video.file_size,
            )
        
        # Audio
        if message.audio:
            return TelegramMediaInfo(
                media_type="audio",
                file_id=message.audio.file_id,
                file_name=message.audio.file_name,
                mime_type=message.audio.mime_type,
                file_size=message.audio.file_size,
            )
        
        # Voice
        if message.voice:
            return TelegramMediaInfo(
                media_type="voice",
                file_id=message.voice.file_id,
                file_name=None,
                mime_type=message.voice.mime_type or "audio/ogg",
                file_size=message.voice.file_size,
            )
        
        # Sticker
        if message.sticker:
            return TelegramMediaInfo(
                media_type="sticker",
                file_id=message.sticker.file_id,
                file_name=None,
                mime_type="image/webp",
                file_size=message.sticker.file_size,
            )
        
        return None
    
    async def download_media(
        self,
        message: Message,
        save_to_workspace: bool = True,
    ) -> tuple[bytes, TelegramMediaInfo] | None:
        """
        Download media from Telegram message.
        
        Args:
            message: Telegram message with media
            save_to_workspace: Whether to save to workspace
        
        Returns:
            (buffer, media_info) or None if no media
        """
        media_info = self.extract_media_info(message)
        if not media_info:
            return None
        
        # Check size limit
        if self.max_bytes and media_info.file_size:
            if media_info.file_size > self.max_bytes:
                logger.warning(
                    f"Media exceeds size limit: {media_info.file_size} > {self.max_bytes}"
                )
                raise ValueError(
                    f"Media too large: {media_info.file_size} bytes (max: {self.max_bytes})"
                )
        
        # Download file
        try:
            file: File = await message.get_bot().get_file(media_info.file_id)
            buffer = await file.download_as_bytearray()
            buffer_bytes = bytes(buffer)
            
            logger.info(
                f"Downloaded Telegram {media_info.media_type}: "
                f"{media_info.file_id[:8]}... ({len(buffer_bytes)} bytes)"
            )
            
            # Save to workspace if requested
            if save_to_workspace and self.media_dir:
                saved_path = await self._save_media(
                    buffer_bytes,
                    media_info
                )
                logger.info(f"Saved to: {saved_path}")
            
            return buffer_bytes, media_info
        
        except Exception as e:
            logger.error(f"Failed to download Telegram media: {e}", exc_info=True)
            raise
    
    async def _save_media(
        self,
        buffer: bytes,
        media_info: TelegramMediaInfo,
    ) -> Path:
        """
        Save media to workspace.
        
        Args:
            buffer: Media buffer
            media_info: Media info
        
        Returns:
            Saved file path
        """
        if not self.media_dir:
            raise RuntimeError("No media directory configured")
        
        # Determine filename
        if media_info.file_name:
            filename = media_info.file_name
        else:
            # Generate filename
            ext = extension_for_mime(media_info.mime_type or "")
            if not ext:
                ext = ".bin"
            filename = f"{media_info.media_type}_{media_info.file_id[:16]}{ext}"
        
        # Save file
        file_path = self.media_dir / filename
        
        # Avoid overwriting
        if file_path.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            counter = 1
            while file_path.exists():
                file_path = self.media_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        
        file_path.write_bytes(buffer)
        
        return file_path
    
    async def get_media_as_data_url(
        self,
        message: Message,
    ) -> tuple[str, TelegramMediaInfo] | None:
        """
        Get media as data URL for direct use in API calls.
        
        Args:
            message: Telegram message with media
        
        Returns:
            (data_url, media_info) or None
        """
        result = await self.download_media(message, save_to_workspace=False)
        if not result:
            return None
        
        buffer, media_info = result
        
        # Encode to base64
        import base64
        b64_data = base64.b64encode(buffer).decode("utf-8")
        
        # Build data URL
        mime = media_info.mime_type or "application/octet-stream"
        data_url = f"data:{mime};base64,{b64_data}"
        
        return data_url, media_info
