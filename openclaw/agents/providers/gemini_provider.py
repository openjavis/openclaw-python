"""
Google Gemini provider implementation using google.genai SDK (NEW API)

Based on: https://ai.google.dev/gemini-api/docs/quickstart
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    GENAI_AVAILABLE = False

from .base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using the NEW google-genai API

    Recommended models (2026):
    - gemini-3-flash-preview    # Latest, fastest (RECOMMENDED)
    - gemini-3-pro-preview      # Most capable
    - gemini-2.5-flash          # Stable, fast
    - gemini-2.5-pro            # Stable, powerful

    Features:
    - Thinking mode support (HIGH/MEDIUM/LOW)
    - Google Search tool integration
    - Streaming responses
    - Multi-turn conversations

    Example:
        provider = GeminiProvider("gemini-3-flash-preview", api_key="...")

        async for response in provider.stream(messages):
            if response.type == "text_delta":
                print(response.content, end="")

    API Documentation:
        https://ai.google.dev/gemini-api/docs/models/gemini
    """

    @property
    def provider_name(self) -> str:
        return "gemini"

    def get_client(self) -> Any:
        """Initialize Gemini client using new API"""
        if self._client is None:
            api_key = self.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not provided")

            if not GENAI_AVAILABLE or genai is None:
                raise ImportError(
                    "google-genai package not installed. Install with: pip install google-genai"
                )

            # Use new google.genai Client
            self._client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})
            logger.info(f"Initialized Gemini client with model: {self.model}")

        return self._client

    def _convert_messages(self, messages: list[LLMMessage]) -> list[types.Content]:
        """Convert messages to Gemini Content format"""
        if not GENAI_AVAILABLE or types is None:
            raise ImportError("google-genai package required")

        gemini_contents = []
        system_instruction = None

        for msg in messages:
            # Extract system message for system_instructions parameter
            if msg.role == "system":
                system_instruction = msg.content
                continue

            # Gemini uses 'user' and 'model' roles
            role = "model" if msg.role == "assistant" else "user"

            # Create Content object
            content = types.Content(role=role, parts=[types.Part.from_text(text=msg.content)])
            gemini_contents.append(content)

        return gemini_contents, system_instruction

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        thinking_mode: str | None = None,  # "HIGH", "MEDIUM", "LOW", or None
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """
        Stream responses from Gemini using new API

        Args:
            messages: List of conversation messages
            tools: Optional tools/functions (not implemented yet)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            thinking_mode: Thinking level ("HIGH", "MEDIUM", "LOW")
            **kwargs: Additional generation parameters
        """
        client = self.get_client()

        try:
            # Convert messages
            contents, system_instruction = self._convert_messages(messages)

            if not contents:
                logger.warning("No messages to send to Gemini")
                return

            # Build generation config
            config_params = {}

            # Add thinking config if specified
            if thinking_mode:
                config_params["thinking_config"] = types.ThinkingConfig(
                    thinking_level=thinking_mode.upper()
                )

            # Add tools if specified (e.g., Google Search)
            if tools or kwargs.get("enable_search"):
                config_params["tools"] = [types.Tool(googleSearch=types.GoogleSearch())]

            # Add generation parameters
            if max_tokens:
                config_params["max_output_tokens"] = max_tokens
            if temperature is not None:
                config_params["temperature"] = temperature

            # Add system instruction if present
            if system_instruction:
                config_params["system_instruction"] = system_instruction

            generate_content_config = types.GenerateContentConfig(**config_params)

            # Use streaming generation
            stream_response = await client.aio.models.generate_content_stream(
                model=self.model,
                contents=contents,
                config=generate_content_config,
            )

            # Stream chunks
            full_text = []
            async for chunk in stream_response:
                if chunk.text:
                    full_text.append(chunk.text)
                    yield LLMResponse(type="text_delta", content=chunk.text)
                    # Fix: Allow event loop to process other tasks in Windows
                    await asyncio.sleep(0.01)  # Yield control to event loop

            # Send completion
            complete_text = "".join(full_text)
            yield LLMResponse(type="done", content=complete_text)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini streaming error: {error_msg}")
            yield LLMResponse(type="error", content=error_msg)

    def _format_tools_for_gemini(self, tools: list[dict] | None) -> list[types.Tool] | None:
        """
        Format tools for Gemini function calling

        Note: Currently only Google Search is supported.
        Custom function calling will be added in future updates.
        """
        if not tools:
            return None

        # For now, only support Google Search
        # Custom tools will be added when Gemini API supports them
        gemini_tools = []

        for tool in tools:
            if tool.get("type") == "google_search":
                gemini_tools.append(types.Tool(googleSearch=types.GoogleSearch()))

        return gemini_tools if gemini_tools else None


# Supported models (2026 update)
GEMINI_MODELS = {
    # Gemini 3.x (Latest - RECOMMENDED)
    "gemini-3-flash-preview": {
        "name": "Gemini 3 Flash Preview",
        "context_window": 1000000,
        "max_output": 8192,
        "features": ["thinking", "search", "vision"],
        "recommended": True,
    },
    "gemini-3-pro-preview": {
        "name": "Gemini 3 Pro Preview",
        "context_window": 2000000,
        "max_output": 8192,
        "features": ["thinking", "search", "vision", "advanced"],
        "recommended": True,
    },
    # Gemini 2.5 (Stable)
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "context_window": 1000000,
        "max_output": 8192,
        "features": ["search", "vision"],
        "stable": True,
    },
    "gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "context_window": 2000000,
        "max_output": 8192,
        "features": ["search", "vision", "advanced"],
        "stable": True,
    },
    # Gemini 2.0
    "gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "context_window": 1000000,
        "max_output": 8192,
        "features": ["search"],
    },
    # Add models/ prefix versions
    "models/gemini-3-flash-preview": {"alias": "gemini-3-flash-preview"},
    "models/gemini-3-pro-preview": {"alias": "gemini-3-pro-preview"},
    "models/gemini-2.5-flash": {"alias": "gemini-2.5-flash"},
    "models/gemini-2.5-pro": {"alias": "gemini-2.5-pro"},
    "models/gemini-2.0-flash": {"alias": "gemini-2.0-flash"},
}
