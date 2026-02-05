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

            # Handle tool messages (function responses)
            if msg.role == "tool":
                # Tool result should be in user role with function_response part
                parts = [types.Part.from_function_response(
                    name=getattr(msg, 'name', 'unknown_function'),
                    response={"result": msg.content}
                )]
                content = types.Content(role="user", parts=parts)
                gemini_contents.append(content)
                continue

            # Gemini uses 'user' and 'model' roles
            role = "model" if msg.role == "assistant" else "user"

            # Create parts list (text + optional images + optional tool calls)
            parts = []
            
            # Add images first (if any)
            if hasattr(msg, 'images') and msg.images:
                for image_url in msg.images:
                    try:
                        # Download image and convert to bytes
                        import httpx
                        response = httpx.get(image_url, timeout=30.0)
                        if response.status_code == 200:
                            image_bytes = response.content
                            # Determine MIME type from URL or content
                            mime_type = "image/jpeg"  # Default
                            if ".png" in image_url.lower():
                                mime_type = "image/png"
                            elif ".gif" in image_url.lower():
                                mime_type = "image/gif"
                            elif ".webp" in image_url.lower():
                                mime_type = "image/webp"
                            
                            # Create image part
                            parts.append(types.Part.from_bytes(
                                data=image_bytes,
                                mime_type=mime_type
                            ))
                            logger.info(f"Added image to Gemini request: {image_url[:50]}...")
                        else:
                            logger.warning(f"Failed to download image: {image_url} (status: {response.status_code})")
                    except Exception as e:
                        logger.error(f"Error loading image {image_url}: {e}")
            
            # Add tool calls if present (for assistant messages)
            if hasattr(msg, 'tool_calls') and msg.tool_calls and role == "model":
                for tc in msg.tool_calls:
                    parts.append(types.Part.from_function_call(
                        name=tc.get("name"),
                        args=tc.get("arguments", {})
                    ))
            
            # Add text content if present
            if msg.content:
                parts.append(types.Part.from_text(text=msg.content))

            # Create Content object with all parts
            if parts:  # Only add if there are parts
                content = types.Content(role=role, parts=parts)
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

            # Add tools if specified
            gemini_tools = []
            if tools:
                # Convert custom tools to Gemini function declarations
                function_declarations = []
                for tool in tools:
                    if tool.get("type") == "function" and "function" in tool:
                        func_spec = tool["function"]
                        function_declarations.append(
                            types.FunctionDeclaration(
                                name=func_spec.get("name"),
                                description=func_spec.get("description", ""),
                                parameters=func_spec.get("parameters", {}),
                            )
                        )
                
                if function_declarations:
                    gemini_tools.append(types.Tool(function_declarations=function_declarations))
                    logger.info(f"Added {len(function_declarations)} function declarations to Gemini")
            
            # Add Google Search if requested
            if kwargs.get("enable_search"):
                if not gemini_tools:
                    gemini_tools = []
                gemini_tools.append(types.Tool(google_search=types.GoogleSearch()))
            
            if gemini_tools:
                config_params["tools"] = gemini_tools
            
            # CRITICAL: Disable Automatic Function Calling when tools is empty or None
            # This prevents Gemini from inventing function calls
            if (tools is None or tools == []) and not kwargs.get("enable_search"):
                config_params["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.NONE
                    )
                )
                logger.info("🚫 AFC disabled - no tool calling allowed")

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
            tool_calls = []
            
            async for chunk in stream_response:
                # Handle text content
                if chunk.text:
                    full_text.append(chunk.text)
                    yield LLMResponse(type="text_delta", content=chunk.text)
                    await asyncio.sleep(0.01)  # Yield control to event loop
                
                # Handle function calls
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            # Check if parts exists and is not None
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'function_call') and part.function_call:
                                        fc = part.function_call
                                        tool_call = {
                                            "id": f"call_{fc.name}_{len(tool_calls)}",
                                            "name": fc.name,
                                            "arguments": dict(fc.args) if fc.args else {}
                                        }
                                        tool_calls.append(tool_call)
                                        logger.info(f"Gemini function call: {fc.name}")

            # Send tool calls if any
            if tool_calls:
                yield LLMResponse(type="tool_call", content=None, tool_calls=tool_calls)

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
