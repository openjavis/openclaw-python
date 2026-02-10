"""Video analysis"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .types import MediaType, AnalysisResult, Provider

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """
    Video analysis
    
    Combines image analysis (keyframes) with audio transcription.
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize video analyzer
        
        Args:
            config: Configuration for providers
        """
        self.config = config or {}
    
    async def analyze(
        self,
        path: Path | str,
        provider: Provider | None = None,
        prompt: str | None = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Analyze video
        
        Args:
            path: Video file path
            provider: Optional provider
            prompt: Optional prompt for frame analysis
            **kwargs: Additional options
            
        Returns:
            Analysis result
        """
        logger.info(f"Analyzing video: {path}")
        
        try:
            # Extract frames
            frames = await self._extract_keyframes(path, kwargs.get("num_frames", 5))
            
            # Analyze frames
            from .image import ImageAnalyzer
            
            image_analyzer = ImageAnalyzer(self.config)
            
            frame_analyses = []
            for i, frame_path in enumerate(frames):
                result = await image_analyzer.analyze(
                    frame_path,
                    provider,
                    prompt or f"Describe this frame from a video (frame {i+1})",
                )
                
                if result.success:
                    frame_analyses.append(result.text)
            
            # Extract audio and transcribe
            audio_path = await self._extract_audio(path)
            
            from .audio import AudioAnalyzer
            
            audio_analyzer = AudioAnalyzer(self.config)
            audio_result = await audio_analyzer.analyze(audio_path)
            
            # Combine results
            combined_text = "Video Analysis:\n\n"
            
            if frame_analyses:
                combined_text += "Visual Description:\n"
                for i, analysis in enumerate(frame_analyses):
                    combined_text += f"Frame {i+1}: {analysis}\n"
            
            if audio_result.success and audio_result.text:
                combined_text += f"\nAudio Transcription:\n{audio_result.text}"
            
            return AnalysisResult(
                media_type=MediaType.VIDEO,
                provider=provider or Provider.ANTHROPIC,
                text=combined_text,
                data={
                    "frames": frame_analyses,
                    "transcription": audio_result.text if audio_result.success else None,
                },
                success=True,
            )
            
        except Exception as e:
            logger.error(f"Video analysis error: {e}", exc_info=True)
            
            return AnalysisResult(
                media_type=MediaType.VIDEO,
                provider=provider or Provider.ANTHROPIC,
                success=False,
                error=str(e),
            )
    
    async def _extract_keyframes(self, video_path: Path | str, num_frames: int = 5) -> list[Path]:
        """
        Extract keyframes from video
        
        Args:
            video_path: Video file path
            num_frames: Number of frames to extract
            
        Returns:
            List of frame image paths
        """
        try:
            import cv2
            import tempfile
        except ImportError:
            raise RuntimeError("opencv-python not installed. Install with: pip install opencv-python")
        
        video = cv2.VideoCapture(str(video_path))
        
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(total_frames // num_frames, 1)
        
        frame_paths = []
        
        for i in range(num_frames):
            frame_num = i * frame_interval
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            
            ret, frame = video.read()
            if not ret:
                break
            
            # Save frame
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                cv2.imwrite(f.name, frame)
                frame_paths.append(Path(f.name))
        
        video.release()
        
        return frame_paths
    
    async def _extract_audio(self, video_path: Path | str) -> Path:
        """
        Extract audio from video
        
        Args:
            video_path: Video file path
            
        Returns:
            Audio file path
        """
        try:
            import ffmpeg
            import tempfile
        except ImportError:
            raise RuntimeError("ffmpeg-python not installed. Install with: pip install ffmpeg-python")
        
        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            audio_path = Path(f.name)
        
        # Extract audio
        (
            ffmpeg
            .input(str(video_path))
            .output(str(audio_path), acodec="libmp3lame", ac=1, ar="16000")
            .overwrite_output()
            .run(quiet=True)
        )
        
        return audio_path
