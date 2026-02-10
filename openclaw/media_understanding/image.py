"""Image analysis"""
from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from .types import MediaType, AnalysisResult, Provider

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Image analysis using vision models"""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize image analyzer
        
        Args:
            config: Configuration for providers
        """
        self.config = config or {}
        self._providers = {}
    
    def _get_provider(self, provider: Provider):
        """Get or create provider instance"""
        if provider not in self._providers:
            if provider == Provider.ANTHROPIC:
                from .providers.anthropic_provider import AnthropicVisionProvider
                self._providers[provider] = AnthropicVisionProvider(
                    api_key=self.config.get("anthropic_api_key")
                )
            elif provider == Provider.OPENAI:
                from .providers.openai_provider import OpenAIVisionProvider
                self._providers[provider] = OpenAIVisionProvider(
                    api_key=self.config.get("openai_api_key")
                )
            elif provider == Provider.GOOGLE:
                from .providers.google_provider import GoogleVisionProvider
                self._providers[provider] = GoogleVisionProvider(
                    api_key=self.config.get("google_api_key")
                )
            else:
                raise ValueError(f"Unsupported image provider: {provider}")
        
        return self._providers[provider]
    
    def _select_provider(self) -> Provider:
        """Select best available provider"""
        # Priority: Anthropic > OpenAI > Google
        for provider in [Provider.ANTHROPIC, Provider.OPENAI, Provider.GOOGLE]:
            try:
                self._get_provider(provider)
                return provider
            except:
                continue
        
        raise RuntimeError("No image analysis provider available")
    
    async def analyze(
        self,
        path: Path | str,
        provider: Provider | None = None,
        prompt: str | None = None,
        **kwargs
    ) -> AnalysisResult:
        """
        Analyze image
        
        Args:
            path: Image file path or URL
            provider: Optional provider (auto-selected if None)
            prompt: Optional prompt for analysis
            **kwargs: Provider-specific options
            
        Returns:
            Analysis result
        """
        # Select provider
        if provider is None:
            provider = self._select_provider()
        
        logger.info(f"Analyzing image with {provider.value}")
        
        try:
            provider_instance = self._get_provider(provider)
            
            # Default prompt if not provided
            if prompt is None:
                prompt = "What's in this image? Describe it in detail."
            
            # Analyze
            result = await provider_instance.analyze_image(path, prompt, **kwargs)
            
            return AnalysisResult(
                media_type=MediaType.IMAGE,
                provider=provider,
                text=result.get("text", ""),
                data=result,
                success=True,
                model=result.get("model"),
            )
            
        except Exception as e:
            logger.error(f"Image analysis error: {e}", exc_info=True)
            
            return AnalysisResult(
                media_type=MediaType.IMAGE,
                provider=provider,
                success=False,
                error=str(e),
            )
    
    @staticmethod
    def load_image_as_base64(path: Path | str) -> str:
        """
        Load image and encode as base64
        
        Args:
            path: Image file path
            
        Returns:
            Base64 encoded image
        """
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    
    @staticmethod
    def get_image_mime_type(path: Path | str) -> str:
        """Get image MIME type"""
        import mimetypes
        
        mime_type, _ = mimetypes.guess_type(str(path))
        return mime_type or "image/jpeg"
