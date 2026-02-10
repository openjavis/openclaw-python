"""Google Cloud TTS provider"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from .base import TTSProvider, TTSVoice

logger = logging.getLogger(__name__)


class GoogleTTSProvider(TTSProvider):
    """Google Cloud TTS provider"""
    
    def __init__(self, credentials_path: str | None = None):
        """
        Initialize Google TTS provider
        
        Args:
            credentials_path: Path to Google Cloud credentials JSON
        """
        super().__init__(api_key=None)
        self.credentials_path = credentials_path
        self._client = None
    
    def _get_client(self):
        """Get or create Google TTS client"""
        if self._client is None:
            try:
                from google.cloud import texttospeech
            except ImportError:
                raise RuntimeError(
                    "google-cloud-texttospeech not installed. "
                    "Install with: pip install google-cloud-texttospeech"
                )
            
            import os
            if self.credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            
            self._client = texttospeech.TextToSpeechClient()
        
        return self._client
    
    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        **kwargs
    ) -> dict:
        """Synthesize speech using Google Cloud TTS"""
        from google.cloud import texttospeech
        
        client = self._get_client()
        
        # Parse voice (format: language_code-voice_name, e.g., en-US-Neural2-A)
        parts = voice.split("-")
        language_code = "-".join(parts[:2]) if len(parts) >= 2 else "en-US"
        voice_name = voice
        
        logger.info(f"Synthesizing with Google TTS: {len(text)} chars, voice={voice}")
        
        # Build synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Build voice params
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )
        
        # Build audio config
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=kwargs.get("speaking_rate", 1.0),
            pitch=kwargs.get("pitch", 0.0),
        )
        
        # Synthesize
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )
        
        # Save to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            f.write(response.audio_content)
        
        return {
            "provider": "google",
            "voice": voice,
            "output_path": str(output_path),
            "characters": len(text),
        }
    
    async def list_voices(self) -> List[TTSVoice]:
        """List available voices"""
        from google.cloud import texttospeech
        
        client = self._get_client()
        
        # Get list of voices
        voices_response = client.list_voices()
        
        voices = []
        for voice_data in voices_response.voices:
            for language_code in voice_data.language_codes:
                voices.append(TTSVoice(
                    id=voice_data.name,
                    name=voice_data.name,
                    language=language_code,
                    gender=voice_data.ssml_gender.name.lower(),
                ))
        
        return voices
    
    def get_default_voice(self) -> str:
        """Get default voice"""
        return "en-US-Neural2-A"
