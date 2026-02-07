"""
MIME type detection and utilities

Matches TypeScript src/media/mime.ts
"""
from __future__ import annotations

import logging
import mimetypes
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class MediaKind(str, Enum):
    """Media type classification (matches TS MediaKind)."""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


# MIME to extension mapping (matches TS EXT_BY_MIME)
EXT_BY_MIME = {
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/x-m4a": ".m4a",
    "audio/mp4": ".m4a",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "application/pdf": ".pdf",
    "application/json": ".json",
    "application/zip": ".zip",
    "application/gzip": ".gz",
    "application/x-tar": ".tar",
    "application/x-7z-compressed": ".7z",
    "application/vnd.rar": ".rar",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "text/csv": ".csv",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

# Extension to MIME mapping
MIME_BY_EXT = {ext: mime for mime, ext in EXT_BY_MIME.items()}
MIME_BY_EXT[".jpeg"] = "image/jpeg"

# Audio file extensions
AUDIO_FILE_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".oga", ".ogg", ".opus", ".wav"}


def normalize_header_mime(mime: str | None) -> str | None:
    """
    Normalize MIME from HTTP header (matches TS normalizeHeaderMime).

    Args:
        mime: MIME type from header

    Returns:
        Normalized MIME type
    """
    if not mime:
        return None
    # Split on ; to remove charset etc.
    cleaned = mime.split(";")[0].strip().lower()
    return cleaned if cleaned else None


def extension_for_mime(mime: str) -> str | None:
    """
    Get file extension for MIME type (matches TS extensionForMime).

    Args:
        mime: MIME type

    Returns:
        File extension (with dot) or None
    """
    mime_lower = mime.lower().strip()
    return EXT_BY_MIME.get(mime_lower)


def mime_for_extension(ext: str) -> str | None:
    """
    Get MIME type for file extension.

    Args:
        ext: File extension (with or without dot)

    Returns:
        MIME type or None
    """
    if not ext.startswith("."):
        ext = f".{ext}"

    ext_lower = ext.lower()

    # Try our mapping first
    if ext_lower in MIME_BY_EXT:
        return MIME_BY_EXT[ext_lower]

    # Fallback to mimetypes
    mime, _ = mimetypes.guess_type(f"file{ext}")
    return mime


def detect_mime(file_path: Path | str | None = None, buffer: bytes | None = None) -> str | None:
    """
    Detect MIME type from file or buffer (matches TS detectMime).

    Args:
        file_path: File path
        buffer: File buffer

    Returns:
        MIME type or None
    """
    # Try file-type detection from buffer (best accuracy)
    if buffer:
        try:
            import filetype
            kind = filetype.guess(buffer)
            if kind:
                return kind.mime
        except ImportError:
            logger.debug("filetype package not available, using fallback")
    # Fallback to extension
    if file_path:
        path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        ext = path_obj.suffix
        if ext:
            mime = mime_for_extension(ext)
            if mime:
                return mime
    # Final fallback to mimetypes
    if file_path:
        mime, _ = mimetypes.guess_type(str(file_path))
        return mime
    return None


def media_kind_from_mime(mime: str | None) -> MediaKind:
    """
    Get media kind from MIME type (matches TS mediaKindFromMime).

    Args:
        mime: MIME type

    Returns:
        MediaKind
    """
    if not mime:
        return MediaKind.UNKNOWN

    mime_lower = mime.lower().strip()

    if mime_lower.startswith("image/"):
        return MediaKind.IMAGE

    if mime_lower.startswith("audio/"):
        return MediaKind.AUDIO

    if mime_lower.startswith("video/"):
        return MediaKind.VIDEO

    # Document types
    if mime_lower in {
        "application/pdf",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/markdown",
        "text/csv",
    }:
        return MediaKind.DOCUMENT
    return MediaKind.UNKNOWN


def is_heic_mime(mime: str | None) -> bool:
    """Check if MIME type is HEIC/HEIF."""
    if not mime:
        return False
    mime_lower = mime.lower().strip()
    return mime_lower in {"image/heic", "image/heif"}


def is_heic_file(file_path: Path | str) -> bool:
    """Check if file is HEIC/HEIF based on extension."""
    path_obj = Path(file_path) if isinstance(file_path, str) else file_path
    ext = path_obj.suffix.lower()
    return ext in {".heic", ".heif"}
