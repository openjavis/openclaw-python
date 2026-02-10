"""Base TTS provider interface"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class TTSVoice:
    """TTS voice information"""
    
    id: str
    name: str
    language: str
    gender: str | None = None
    description: str | None = None


class TTSProvider(ABC):
    """Base class for TTS providers"""
    
    def __init__(self, api_key: str | None = None):
        """
        Initialize TTS provider
        
        Args:
            api_key: Optional API key
        """
        self.api_key = api_key
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_path: Path,
        voice: str,
        **kwargs
    ) -> dict:
        """
        Synthesize speech
        
        Args:
            text: Text to synthesize
            output_path: Output file path
            voice: Voice ID
            **kwargs: Provider-specific options
            
        Returns:
            Result metadata
        """
        pass
    
    @abstractmethod
    async def list_voices(self) -> List[TTSVoice]:
        """
        List available voices
        
        Returns:
            List of voices
        """
        pass
    
    @abstractmethod
    def get_default_voice(self) -> str:
        """Get default voice ID"""
        pass
