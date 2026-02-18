import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from openclaw.agents.providers.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GoogleGenAIProvider(LLMProvider):
    """Legacy Google provider using streamGenerateContent REST endpoint."""

    @property
    def provider_name(self) -> str:
        return "google"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3-flash-preview",
        base_url: str = "https://aiplatform.googleapis.com/v1/publishers/google/models",
    ):
        resolved_api_key = api_key or os.getenv("CLAWDBOT_GOOGLE_API_KEY")
        super().__init__(model=model, api_key=resolved_api_key, base_url=base_url)

    def get_client(self) -> httpx.AsyncClient:
        """Create HTTP client used for this stream call."""
        return httpx.AsyncClient(timeout=60.0)

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 65535,
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """Stream responses from Gemini REST API."""
        if not self.api_key:
            raise ValueError("Google API key is required")

        url = f"{self.base_url}/{self.model}:streamGenerateContent?key={self.api_key}"

        contents = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            if msg.role == "system":
                role = "user"

            parts = [{"text": msg.content}]
            contents.append({"role": role, "parts": parts})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 1.0),
                "maxOutputTokens": max_tokens,
                "topP": kwargs.get("top_p", 0.95),
                "thinkingConfig": {"thinkingLevel": "HIGH"},
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"},
            ],
        }

        headers = {"Content-Type": "application/json"}

        async with self.get_client() as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Gemini API Error: {response.status_code} - {error_text}")
                    raise Exception(f"Gemini API Error: {response.status_code}")

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    cleaned_line = line.strip()
                    if cleaned_line.startswith("["):
                        cleaned_line = cleaned_line[1:]
                    if cleaned_line.endswith("]"):
                        cleaned_line = cleaned_line[:-1]
                    if cleaned_line.endswith(","):
                        cleaned_line = cleaned_line[:-1]

                    if not cleaned_line:
                        continue

                    try:
                        data = json.loads(cleaned_line)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON chunk: {cleaned_line[:100]}...")
                        continue

                    candidates = data.get("candidates", [])
                    if not candidates:
                        continue

                    candidate = candidates[0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        if "text" in part:
                            yield LLMResponse(type="text_delta", content=part["text"])

                    finish_reason = candidate.get("finishReason")
                    if finish_reason:
                        yield LLMResponse(
                            type="done",
                            content=None,
                            finish_reason=str(finish_reason),
                        )
