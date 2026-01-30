"""
OpenAI provider implementation
"""

import logging
import os
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from .base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI provider

    Supports:
    - GPT-4, GPT-4 Turbo
    - GPT-3.5 Turbo
    - o1, o1-mini, o1-preview
    - Any OpenAI-compatible API (via base_url)

    Example:
        # OpenAI
        provider = OpenAIProvider("gpt-4", api_key="...")

        # OpenAI-compatible (e.g., LM Studio, Ollama with OpenAI compat)
        provider = OpenAIProvider(
            "model-name",
            base_url="http://localhost:1234/v1"
        )
    """

    @property
    def provider_name(self) -> str:
        return "openai"

    def get_client(self) -> AsyncOpenAI:
        """Get OpenAI client"""
        if self._client is None:
            api_key = self.api_key or os.getenv("OPENAI_API_KEY", "not-needed")

            # Support custom base URL for OpenAI-compatible APIs
            kwargs = {"api_key": api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url

            self._client = AsyncOpenAI(**kwargs)

        return self._client

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """Stream responses from OpenAI"""
        client = self.get_client()

        # Convert messages to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_messages.append({"role": msg.role, "content": msg.content})

        try:
            # Build request parameters
            params = {
                "model": self.model,
                "messages": openai_messages,
                "max_tokens": max_tokens,
                "stream": True,
                **kwargs,
            }

            # Add tools if provided
            if tools:
                params["tools"] = tools

            # Start streaming
            stream = await client.chat.completions.create(**params)

            # Track tool calls
            tool_calls_buffer = {}

            async for chunk in stream:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # Text content
                if delta.content:
                    yield LLMResponse(type="text_delta", content=delta.content)

                # Tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        idx = tool_call.index

                        # Initialize buffer for this tool call
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": tool_call.id or f"call_{idx}",
                                "name": "",
                                "arguments": "",
                            }

                        # Accumulate function name
                        if tool_call.function and tool_call.function.name:
                            tool_calls_buffer[idx]["name"] = tool_call.function.name

                        # Accumulate arguments
                        if tool_call.function and tool_call.function.arguments:
                            tool_calls_buffer[idx]["arguments"] += tool_call.function.arguments

                # Check if done
                if choice.finish_reason:
                    # Emit tool calls if any
                    if tool_calls_buffer:
                        import json

                        tool_calls = []
                        for tc in tool_calls_buffer.values():
                            try:
                                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                            except json.JSONDecodeError:
                                args = {}

                            tool_calls.append(
                                {"id": tc["id"], "name": tc["name"], "arguments": args}
                            )

                        yield LLMResponse(type="tool_call", content=None, tool_calls=tool_calls)

                    yield LLMResponse(type="done", content=None, finish_reason=choice.finish_reason)

        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield LLMResponse(type="error", content=str(e))
