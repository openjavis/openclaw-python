"""OpenAI vision and audio providers"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class OpenAIVisionProvider:
    """OpenAI GPT-4 vision provider"""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client
    
    async def analyze_image(self, path: Path | str, prompt: str, **kwargs) -> dict:
        """Analyze image with GPT-4V"""
        import base64
        
        client = self._get_client()
        model = kwargs.get("model", "gpt-4o")
        
        # Load image
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # Analyze
        response = await client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }],
            max_tokens=kwargs.get("max_tokens", 1024),
        )
        
        return {
            "text": response.choices[0].message.content,
            "model": model,
        }


class OpenAIAudioProvider:
    """OpenAI Whisper provider"""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client
    
    async def transcribe(self, path: Path | str, **kwargs) -> dict:
        """Transcribe audio with Whisper"""
        client = self._get_client()
        model = kwargs.get("model", "whisper-1")
        
        with open(path, "rb") as f:
            transcript = await client.audio.transcriptions.create(
                model=model,
                file=f,
                language=kwargs.get("language"),
            )
        
        return {
            "text": transcript.text,
            "model": model,
        }
