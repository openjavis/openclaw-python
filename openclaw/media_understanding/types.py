"""Media Understanding types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class MediaScope(str, Enum):
    """Scope for media understanding."""

    AUTO = "auto"  # Automatic based on config
    ALL = "all"  # Process all media
    IMAGES = "images"  # Only images
    AUDIO = "audio"  # Only audio
    VIDEO = "video"  # Only video
    NONE = "none"  # No media understanding


@dataclass
class MediaUnderstandingResult:
    """Result of media understanding."""

    media_type: Literal["image", "audio", "video"]
    url: str
    description: str | None = None
    transcript: str | None = None
    error: str | None = None
    provider: str | None = None
    model: str | None = None
