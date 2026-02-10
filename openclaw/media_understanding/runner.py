"""Main media understanding runner"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any

from .types import MediaType, AnalysisResult, Provider
from .image import ImageAnalyzer
from .audio import AudioAnalyzer
from .video import VideoAnalyzer

logger = logging.getLogger(__name__)


class MediaUnderstandingRunner:
    """
    Main coordinator for media analysis
    
    Auto-detects media type and routes to appropriate analyzer.
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize media understanding runner
        
        Args:
            config: Optional configuration for providers
        """
        self.config = config or {}
        
        # Initialize analyzers
        self.image_analyzer = ImageAnalyzer(config)
        self.audio_analyzer = AudioAnalyzer(config)
        self.video_analyzer = VideoAnalyzer(config)
    
    def detect_media_type(self, path: Path | str) -> MediaType:
        """
        Detect media type from file path
        
        Args:
            path: File path or URL
            
        Returns:
            Detected media type
        """
        path_str = str(path)
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(path_str)
        
        if mime_type:
            if mime_type.startswith("image/"):
                return MediaType.IMAGE
            elif mime_type.startswith("audio/"):
                return MediaType.AUDIO
            elif mime_type.startswith("video/"):
                return MediaType.VIDEO
        
        # Fallback to extension
        ext = Path(path_str).suffix.lower()
        
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
        audio_exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
        video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
        
        if ext in image_exts:
            return MediaType.IMAGE
        elif ext in audio_exts:
            return MediaType.AUDIO
        elif ext in video_exts:
            return MediaType.VIDEO
        
        return MediaType.UNKNOWN
    
    async def analyze(
        self,
        path: Path | str,
        media_type: MediaType | None = None,
        provider: Provider | None = None,
        prompt: str | None = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Analyze media
        
        Args:
            path: File path or URL
            media_type: Optional media type (auto-detected if None)
            provider: Optional provider (auto-selected if None)
            prompt: Optional prompt for analysis
            **kwargs: Additional provider-specific options
            
        Returns:
            Analysis result
        """
        import time
        
        start_time = time.time()
        
        # Detect media type if not provided
        if media_type is None:
            media_type = self.detect_media_type(path)
        
        logger.info(f"Analyzing {media_type.value}: {path}")
        
        try:
            # Route to appropriate analyzer
            if media_type == MediaType.IMAGE:
                result = await self.image_analyzer.analyze(
                    path, provider, prompt, **kwargs
                )
            elif media_type == MediaType.AUDIO:
                result = await self.audio_analyzer.analyze(
                    path, provider, **kwargs
                )
            elif media_type == MediaType.VIDEO:
                result = await self.video_analyzer.analyze(
                    path, provider, prompt, **kwargs
                )
            else:
                result = AnalysisResult(
                    media_type=media_type,
                    provider=Provider.ANTHROPIC,  # Placeholder
                    success=False,
                    error=f"Unsupported media type: {media_type}",
                )
            
            # Add duration
            result.duration_ms = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            logger.error(f"Media analysis error: {e}", exc_info=True)
            
            return AnalysisResult(
                media_type=media_type,
                provider=provider or Provider.ANTHROPIC,
                success=False,
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )


# Convenience function
async def analyze_media(
    path: Path | str,
    prompt: str | None = None,
    **kwargs
) -> AnalysisResult:
    """
    Analyze media (convenience function)
    
    Args:
        path: File path or URL
        prompt: Optional prompt
        **kwargs: Additional options
        
    Returns:
        Analysis result
    """
    runner = MediaUnderstandingRunner()
    return await runner.analyze(path, prompt=prompt, **kwargs)
