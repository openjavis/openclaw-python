"""Type definitions for media understanding"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MediaType(str, Enum):
    """Media type"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    UNKNOWN = "unknown"


class Provider(str, Enum):
    """Analysis provider"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    DEEPGRAM = "deepgram"
    GROQ = "groq"
    MINIMAX = "minimax"


@dataclass
class AnalysisResult:
    """Media analysis result"""
    
    media_type: MediaType
    provider: Provider
    
    # Text description/transcription
    text: str = ""
    
    # Structured data
    data: dict[str, Any] = field(default_factory=dict)
    
    # Confidence score (0-1)
    confidence: float | None = None
    
    # Processing metadata
    duration_ms: float | None = None
    model: str | None = None
    
    # Error information
    error: str | None = None
    success: bool = True
