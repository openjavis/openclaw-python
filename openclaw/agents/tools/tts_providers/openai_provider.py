"""OpenAI TTS provider"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from .base import TTSProvider, TTSVoice

logger = logging.getLogger(__name__)


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider"""
    
    VOICES = [
        TTSVoice(id="alloy", name="Alloy", language="en", gender="neutral"),
        TTSVoice(id="echo", name="Echo", language="en", gender="male"),
        TTSVoice(id="fable", name="Fable", language="en", gender="neutral"),
        TTSVoice(id="onyx", name="Onyx", language="en", gender="male"),
        TTSVoice(id="nova", name="Nova", language="en", gender="female"),
        TTSVoice(id="shimmer", name="Shimmer", language="en", gender="female"),
    ]
    
    def __init__(self, api_key: str | None = None, model: str = "tts-1"):
        """
        Initialize OpenAI TTS provider
        
        Args:
            api_key: OpenAI API key
            model: Model to use (tts-1 or tts-1-hd)
        """
        super().__init__(api_key)
        self.model = model
        self._client = None
    
    def _get_client(self):
        """Get or create OpenAI client"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise RuntimeError("openai package not installed")
            
            self._client = AsyncOpenAI(api_key=self.api_key)
        
        return self._client
    
    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        **kwargs
    ) -> dict:
        """Synthesize speech using OpenAI"""
        client = self._get_client()
        
        model = kwargs.get("model", self.model)
        speed = kwargs.get("speed", 1.0)
        
        logger.info(f"Synthesizing with OpenAI: {len(text)} chars, voice={voice}")
        
        response = await client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed,
        )
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response.stream_to_file(str(output_path))
        
        return {
            "provider": "openai",
            "model": model,
            "voice": voice,
            "output_path": str(output_path),
            "characters": len(text),
        }
    
    async def list_voices(self) -> List[TTSVoice]:
        """List available voices"""
        return self.VOICES.copy()
    
    def get_default_voice(self) -> str:
        """Get default voice"""
        return "alloy"
