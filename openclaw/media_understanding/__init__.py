"""Media Understanding - Automatic audio/video/image analysis.

Aligned with TypeScript src/media-understanding/
"""

from __future__ import annotations

from .apply import apply_media_understanding
from .runner import run_media_understanding
from .types import MediaScope, MediaUnderstandingResult

__all__ = [
    "MediaUnderstandingResult",
    "MediaScope",
    "run_media_understanding",
    "apply_media_understanding",
]
