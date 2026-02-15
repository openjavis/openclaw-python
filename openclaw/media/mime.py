"""MIME type detection and media kind classification.

Matches TypeScript src/media/mime.ts and src/media/constants.ts
"""

from __future__ import annotations

import mimetypes
from enum import Enum
from pathlib import Path
from typing import Optional

# Initialize mimetypes
mimetypes.init()


class MediaKind(str, Enum):
    """Media kind enum"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


# MIME type to extension mapping
EXT_BY_MIME = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/x-msvideo": ".avi",
    "video/webm": ".webm",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/webm": ".weba",
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


# Extension to MIME type mapping
MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".weba": "audio/webm",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


def normalize_header_mime(mime: Optional[str]) -> Optional[str]:
    """Normalize MIME type from HTTP header.

    Args:
        mime: MIME type string (may contain charset, etc.)

    Returns:
        Normalized MIME type or None
    """
    if not mime:
        return None

    # Remove charset and other parameters
    normalized = mime.split(";")[0].strip()

    return normalized if normalized else None


def extension_for_mime(mime_type: Optional[str]) -> Optional[str]:
    """Get file extension for MIME type.

    Args:
        mime_type: MIME type string

    Returns:
        File extension (with dot) or None
    """
    if not mime_type:
        return None

    # Normalize
    mime_lower = mime_type.lower().strip()

    # Look up in our mapping
    return EXT_BY_MIME.get(mime_lower)


def mime_for_extension(ext: str) -> Optional[str]:
    """Get MIME type for file extension.

    Args:
        ext: File extension (with or without dot)

    Returns:
        MIME type or None
    """
    if not ext:
        return None

    # Ensure leading dot
    if not ext.startswith("."):
        ext = f".{ext}"

    ext_lower = ext.lower()

    # Look up in our mapping first
    mime = MIME_BY_EXT.get(ext_lower)
    if mime:
        return mime

    # Fall back to mimetypes module
    mime_type, _ = mimetypes.guess_type(f"file{ext_lower}")
    return mime_type


def detect_mime(file_path: Path | str, content_type: Optional[str] = None) -> Optional[str]:
    """Detect MIME type from file path and/or content type.

    Args:
        file_path: File path (for extension detection)
        content_type: Optional content type from HTTP header

    Returns:
        MIME type or None
    """
    # Prefer explicit content_type
    if content_type:
        normalized = normalize_header_mime(content_type)
        if normalized:
            return normalized

    # Fall back to extension detection
    if isinstance(file_path, str):
        file_path = Path(file_path)

    return mime_for_extension(file_path.suffix)


def media_kind_from_mime(content_type: Optional[str]) -> MediaKind:
    """Determine media kind from MIME type.

    Args:
        content_type: MIME type string

    Returns:
        Media kind
    """
    if not content_type:
        return MediaKind.UNKNOWN

    content_type_lower = content_type.lower().split(";")[0].strip()

    if content_type_lower.startswith("image/"):
        return MediaKind.IMAGE
    elif content_type_lower.startswith("video/"):
        return MediaKind.VIDEO
    elif content_type_lower.startswith("audio/"):
        return MediaKind.AUDIO
    elif content_type_lower.startswith("application/") or content_type_lower.startswith("text/"):
        return MediaKind.DOCUMENT
    else:
        return MediaKind.UNKNOWN


def is_heic_mime(mime_type: Optional[str]) -> bool:
    """Check if MIME type is HEIC/HEIF.

    Args:
        mime_type: MIME type string

    Returns:
        True if HEIC/HEIF
    """
    if not mime_type:
        return False

    mime_lower = mime_type.lower()
    return "heic" in mime_lower or "heif" in mime_lower


def is_heic_file(file_path: Path) -> bool:
    """Check if file is HEIC/HEIF by extension.

    Args:
        file_path: File path

    Returns:
        True if HEIC/HEIF
    """
    ext = file_path.suffix.lower()
    return ext in [".heic", ".heif"]


def is_gif_media(content_type: Optional[str], file_name: Optional[str]) -> bool:
    """Check if media is a GIF animation.

    Args:
        content_type: MIME type
        file_name: File name

    Returns:
        True if GIF
    """
    if content_type:
        content_type_lower = content_type.lower()
        if "image/gif" in content_type_lower:
            return True

    if file_name:
        file_name_lower = file_name.lower()
        if file_name_lower.endswith(".gif"):
            return True

    return False
