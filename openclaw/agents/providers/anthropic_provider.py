"""
Anthropic Claude provider implementation
"""

import logging
import os
from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic

from .base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude provider

    Supports all Claude models:
    - claude-opus-4-5
    - claude-sonnet-4-5
    - claude-3-5-sonnet
    - etc.
    """

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def get_client(self) -> AsyncAnthropic:
        """Get Anthropic client"""
        if self._client is None:
            api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not provided")

            self._client = AsyncAnthropic(api_key=api_key)

        return self._client

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """Stream responses from Anthropic"""
        client = self.get_client()

        # Convert messages to Anthropic format
        anthropic_messages = []
        for msg in messages:
            if msg.role != "system":  # System handled separately
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        # Extract system message
        system = None
        system_msgs = [m for m in messages if m.role == "system"]
        if system_msgs:
            system = system_msgs[0].content

        try:
            # Start streaming
            async with client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                messages=anthropic_messages,
                system=system,
                tools=tools,
                **kwargs,
            ) as stream:
                async for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            if hasattr(event.delta, "text"):
                                yield LLMResponse(type="text_delta", content=event.delta.text)
                        elif event.type == "content_block_start":
                            if (
                                hasattr(event.content_block, "type")
                                and event.content_block.type == "tool_use"
                            ):
                                # Tool call started
                                pass

                # Get final message
                final_message = await stream.get_final_message()

                # Check for tool calls
                tool_calls = []
                for block in final_message.content:
                    if block.type == "tool_use":
                        tool_calls.append(
                            {"id": block.id, "name": block.name, "arguments": block.input}
                        )

                if tool_calls:
                    yield LLMResponse(type="tool_call", content=None, tool_calls=tool_calls)

                yield LLMResponse(
                    type="done", content=None, finish_reason=final_message.stop_reason
                )

        except Exception as e:
            logger.error(f"Anthropic streaming error: {e}")
            yield LLMResponse(type="error", content=str(e))
