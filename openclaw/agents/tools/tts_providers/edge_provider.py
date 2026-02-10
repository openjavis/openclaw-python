"""Edge TTS provider (free Microsoft TTS)"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from .base import TTSProvider, TTSVoice

logger = logging.getLogger(__name__)


class EdgeTTSProvider(TTSProvider):
    """
    Edge TTS provider
    
    Uses Microsoft Edge's free TTS service (no API key required).
    """
    
    # Popular voices (full list available via edge-tts --list-voices)
    POPULAR_VOICES = [
        TTSVoice(id="en-US-AriaNeural", name="Aria (US English)", language="en-US", gender="female"),
        TTSVoice(id="en-US-GuyNeural", name="Guy (US English)", language="en-US", gender="male"),
        TTSVoice(id="en-GB-SoniaNeural", name="Sonia (UK English)", language="en-GB", gender="female"),
        TTSVoice(id="en-GB-RyanNeural", name="Ryan (UK English)", language="en-GB", gender="male"),
        TTSVoice(id="zh-CN-XiaoxiaoNeural", name="Xiaoxiao (Chinese)", language="zh-CN", gender="female"),
        TTSVoice(id="zh-CN-YunxiNeural", name="Yunxi (Chinese)", language="zh-CN", gender="male"),
        TTSVoice(id="ja-JP-NanamiNeural", name="Nanami (Japanese)", language="ja-JP", gender="female"),
        TTSVoice(id="ko-KR-SunHiNeural", name="SunHi (Korean)", language="ko-KR", gender="female"),
    ]
    
    def __init__(self):
        """Initialize Edge TTS provider"""
        super().__init__(api_key=None)  # No API key needed
    
    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        **kwargs
    ) -> dict:
        """Synthesize speech using Edge TTS"""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError(
                "edge-tts not installed. Install with: pip install edge-tts"
            )
        
        logger.info(f"Synthesizing with Edge TTS: {len(text)} chars, voice={voice}")
        
        # Create communicate instance
        communicate = edge_tts.Communicate(text, voice)
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(str(output_path))
        
        return {
            "provider": "edge",
            "voice": voice,
            "output_path": str(output_path),
            "characters": len(text),
        }
    
    async def list_voices(self) -> List[TTSVoice]:
        """List available voices"""
        try:
            import edge_tts
        except ImportError:
            return self.POPULAR_VOICES
        
        # Get full voice list
        voices_data = await edge_tts.list_voices()
        
        voices = []
        for voice_data in voices_data:
            voices.append(TTSVoice(
                id=voice_data["ShortName"],
                name=voice_data["FriendlyName"],
                language=voice_data["Locale"],
                gender=voice_data.get("Gender", "").lower(),
            ))
        
        return voices
    
    def get_default_voice(self) -> str:
        """Get default voice"""
        return "en-US-AriaNeural"
