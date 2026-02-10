"""Anthropic vision provider"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AnthropicVisionProvider:
    """Anthropic Claude vision provider"""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client
    
    async def analyze_image(self, path: Path | str, prompt: str, **kwargs) -> dict:
        """Analyze image with Claude"""
        import base64
        
        client = self._get_client()
        model = kwargs.get("model", "claude-3-5-sonnet-20241022")
        
        # Load image
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # Get mime type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(path))
        
        # Analyze
        response = await client.messages.create(
            model=model,
            max_tokens=kwargs.get("max_tokens", 1024),
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type or "image/jpeg",
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        
        return {
            "text": response.content[0].text,
            "model": model,
        }
