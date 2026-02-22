"""
Thinking mode support for extracting AI reasoning
"""

from .extractor import ThinkingExtractor
from .modes import ThinkingMode

# Re-export ThinkingLevel from agents.types for convenience
try:
    from ..types import ThinkingLevel
except ImportError:
    from enum import Enum

    class ThinkingLevel(str, Enum):  # type: ignore[no-redef]
        NONE = "none"
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"

__all__ = ["ThinkingExtractor", "ThinkingMode", "ThinkingLevel"]
