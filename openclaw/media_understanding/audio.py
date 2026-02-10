"""Audio analysis (transcription)"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .types import MediaType, AnalysisResult, Provider

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """Audio analysis using STT models"""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize audio analyzer
        
        Args:
            config: Configuration for providers
        """
        self.config = config or {}
        self._providers = {}
    
    def _get_provider(self, provider: Provider):
        """Get or create provider instance"""
        if provider not in self._providers:
            if provider == Provider.DEEPGRAM:
                from .providers.deepgram_provider import DeepgramProvider
                self._providers[provider] = DeepgramProvider(
                    api_key=self.config.get("deepgram_api_key")
                )
            elif provider == Provider.OPENAI:
                from .providers.openai_provider import OpenAIAudioProvider
                self._providers[provider] = OpenAIAudioProvider(
                    api_key=self.config.get("openai_api_key")
                )
            elif provider == Provider.GROQ:
                from .providers.groq_provider import GroqAudioProvider
                self._providers[provider] = GroqAudioProvider(
                    api_key=self.config.get("groq_api_key")
                )
            else:
                raise ValueError(f"Unsupported audio provider: {provider}")
        
        return self._providers[provider]
    
    def _select_provider(self) -> Provider:
        """Select best available provider"""
        # Priority: Deepgram > Groq > OpenAI
        for provider in [Provider.DEEPGRAM, Provider.GROQ, Provider.OPENAI]:
            try:
                self._get_provider(provider)
                return provider
            except:
                continue
        
        raise RuntimeError("No audio analysis provider available")
    
    async def analyze(
        self,
        path: Path | str,
        provider: Provider | None = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Analyze audio (transcribe)
        
        Args:
            path: Audio file path or URL
            provider: Optional provider (auto-selected if None)
            **kwargs: Provider-specific options
            
        Returns:
            Analysis result with transcription
        """
        # Select provider
        if provider is None:
            provider = self._select_provider()
        
        logger.info(f"Transcribing audio with {provider.value}")
        
        try:
            provider_instance = self._get_provider(provider)
            
            # Transcribe
            result = await provider_instance.transcribe(path, **kwargs)
            
            return AnalysisResult(
                media_type=MediaType.AUDIO,
                provider=provider,
                text=result.get("text", ""),
                data=result,
                success=True,
                model=result.get("model"),
                confidence=result.get("confidence"),
            )
            
        except Exception as e:
            logger.error(f"Audio analysis error: {e}", exc_info=True)
            
            return AnalysisResult(
                media_type=MediaType.AUDIO,
                provider=provider,
                success=False,
                error=str(e),
            )
