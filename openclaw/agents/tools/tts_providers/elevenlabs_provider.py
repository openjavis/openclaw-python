"""ElevenLabs TTS provider"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from .base import TTSProvider, TTSVoice

logger = logging.getLogger(__name__)


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs TTS provider"""
    
    def __init__(self, api_key: str | None = None):
        """
        Initialize ElevenLabs TTS provider
        
        Args:
            api_key: ElevenLabs API key
        """
        super().__init__(api_key)
        self._client = None
    
    def _get_client(self):
        """Get or create ElevenLabs client"""
        if self._client is None:
            try:
                from elevenlabs.client import ElevenLabs
            except ImportError:
                raise RuntimeError(
                    "elevenlabs package not installed. "
                    "Install with: pip install elevenlabs"
                )
            
            self._client = ElevenLabs(api_key=self.api_key)
        
        return self._client
    
    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        **kwargs
    ) -> dict:
        """Synthesize speech using ElevenLabs"""
        client = self._get_client()
        
        model = kwargs.get("model", "eleven_monolingual_v1")
        stability = kwargs.get("stability", 0.5)
        similarity_boost = kwargs.get("similarity_boost", 0.5)
        
        logger.info(f"Synthesizing with ElevenLabs: {len(text)} chars, voice={voice}")
        
        # Generate audio
        audio = client.generate(
            text=text,
            voice=voice,
            model=model,
            voice_settings={
                "stability": stability,
                "similarity_boost": similarity_boost,
            }
        )
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        
        return {
            "provider": "elevenlabs",
            "model": model,
            "voice": voice,
            "output_path": str(output_path),
            "characters": len(text),
        }
    
    async def list_voices(self) -> List[TTSVoice]:
        """List available voices"""
        client = self._get_client()
        
        voices_data = client.voices.get_all()
        
        voices = []
        for voice_data in voices_data.voices:
            voices.append(TTSVoice(
                id=voice_data.voice_id,
                name=voice_data.name,
                language="en",  # ElevenLabs primarily English
                description=voice_data.labels.get("description"),
            ))
        
        return voices
    
    def get_default_voice(self) -> str:
        """Get default voice"""
        return "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
