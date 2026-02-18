import json
import logging
import os
from typing import AsyncIterator, Any

import httpx
from openclaw.agents.providers.base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class GoogleGenAIProvider(LLMProvider):
    """
    Provider for Google's Gemini models using the native REST API.
    Supports streamGenerateContent and thinkingConfig.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3-flash-preview",
        base_url: str = "https://aiplatform.googleapis.com/v1/publishers/google/models",
    ):
        self.api_key = api_key or os.getenv("CLAWDBOT_GOOGLE_API_KEY")
        self.model = model
        self.base_url = base_url

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 65535,
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """
        Stream responses from Gemini API
        """
        if not self.api_key:
            raise ValueError("Google API key is required")

        url = f"{self.base_url}/{self.model}:streamGenerateContent?key={self.api_key}"
        
        # Convert messages to Google format
        contents = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            if msg.role == "system":
                # Gemini doesn't have system role in contents, usually passed separately or prepended
                # For simplicity in this native impl, we prepend to first user message or handle as user
                # But correct way for Gemini 1.5+ is system_instruction, checking if supported by this endpoint
                # The user's curl didn't show system_instruction, so let's check later.
                # For now, treat as user role or prepend.
                role = "user" 
            
            parts = [{"text": msg.content}]
            contents.append({"role": role, "parts": parts})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 1.0),
                "maxOutputTokens": max_tokens,
                "topP": kwargs.get("top_p", 0.95),
                "thinkingConfig": {
                    "thinkingLevel": "HIGH"
                }
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "OFF"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "OFF"}
            ]
        }

        # Handle tools if provided (future)
        # if tools: ...

        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, headers=headers, timeout=60.0) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Gemini API Error: {response.status_code} - {error_text}")
                    raise Exception(f"Gemini API Error: {response.status_code}")

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    # line usually starts with "data: " for SSE, but Google's stream might be a JSON list
                    # Verify format. standard `streamGenerateContent` returns a JSON array of objects if not SSE
                    # But often it is just a stream of JSON objects.
                    # Let's try to parse the line.
                    
                    # Note: httpx stream might chunk raw bytes. aiter_lines handles newlines.
                    # Google API typically returns a JSON list `[...]`. We need to handle the array brackets.
                    
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
                        candidates = data.get("candidates", [])
                        if candidates:
                            candidate = candidates[0]
                            content = candidate.get("content", {})
                            parts = content.get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield LLMResponse(text_delta=part["text"])
                            
                            finish_reason = candidate.get("finishReason")
                            if finish_reason and finish_reason != "STOP":
                                # yield LLMResponse(finish_reason=finish_reason)
                                pass
                                
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON chunk: {cleaned_line[:100]}...")
                        continue

