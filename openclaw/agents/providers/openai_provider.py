"""
OpenAI provider implementation
"""

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

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

    def _get_gcp_token(self) -> str:
        """Get GCP access token using ADC"""
        try:
            import google.auth
            from google.auth.transport.requests import Request

            credentials, project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())
            return credentials.token
        except Exception as e:
            logger.error(f"Failed to get GCP token: {e}")
            raise

    def get_client(self) -> AsyncOpenAI:
        """Get OpenAI client"""
        # Check if we need to use GCP ADC
        # If configured with "gcp_adc" or based on flag, we refresh token every time
        api_key = self.api_key or os.getenv("OPENAI_API_KEY", "not-needed")

        use_adc = api_key == "gcp_adc" or os.getenv("CLAWDBOT_AGENT__API_KEY") == "gcp_adc"

        if use_adc:
            # Always get fresh token for ADC
            api_key = self._get_gcp_token()
            return AsyncOpenAI(api_key=api_key, base_url=self.base_url)

        # Standard static client caching
        if self._client is None:
            # Support custom base URL for OpenAI-compatible APIs
            kwargs = {"api_key": api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url

            self._client = AsyncOpenAI(**kwargs)

        return self._client

    def _serialize_tool_call(self, tool_call: dict[str, Any], fallback_id: str) -> dict[str, Any]:
        """Normalize tool call shape for OpenAI Chat Completions."""
        tool_call_id = str(tool_call.get("id") or fallback_id)

        function_payload = tool_call.get("function")
        if isinstance(function_payload, dict):
            function_name = str(
                function_payload.get("name") or tool_call.get("name") or "unknown_tool"
            )
            function_args = function_payload.get("arguments", tool_call.get("arguments", {}))
        else:
            function_name = str(tool_call.get("name") or "unknown_tool")
            function_args = tool_call.get("arguments", {})

        if isinstance(function_args, str):
            arguments_json = function_args
        else:
            try:
                arguments_json = json.dumps(function_args if function_args is not None else {})
            except TypeError:
                arguments_json = json.dumps({"value": str(function_args)})

        return {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": function_name,
                "arguments": arguments_json,
            },
        }

    def _convert_messages(self, messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert runtime LLM messages to OpenAI chat message schema."""
        openai_messages: list[dict[str, Any]] = []

        for msg_idx, msg in enumerate(messages):
            role = msg.role

            if role == "assistant":
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.content if msg.content is not None else "",
                }

                if msg.tool_calls:
                    normalized_tool_calls = []
                    for tool_idx, tool_call in enumerate(msg.tool_calls):
                        if not isinstance(tool_call, dict):
                            logger.warning(
                                "Skipping non-dict tool_call at message %s index %s: %r",
                                msg_idx,
                                tool_idx,
                                tool_call,
                            )
                            continue
                        normalized_tool_calls.append(
                            self._serialize_tool_call(
                                tool_call, fallback_id=f"call_{msg_idx}_{tool_idx}"
                            )
                        )
                    if normalized_tool_calls:
                        assistant_message["tool_calls"] = normalized_tool_calls
                        # OpenAI allows `content=None` when tool calls are present.
                        if assistant_message["content"] == "":
                            assistant_message["content"] = None

                openai_messages.append(assistant_message)
                continue

            if role == "tool":
                if not msg.tool_call_id:
                    logger.warning(
                        "Skipping tool message without tool_call_id at index %s to avoid OpenAI 400",
                        msg_idx,
                    )
                    continue

                tool_message: dict[str, Any] = {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content if msg.content is not None else "",
                }
                if msg.name:
                    tool_message["name"] = msg.name
                openai_messages.append(tool_message)
                continue

            # user/system/developer or other roles pass through with safe string content
            openai_messages.append(
                {
                    "role": role,
                    "content": msg.content if msg.content is not None else "",
                }
            )

        return openai_messages

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
        openai_messages = self._convert_messages(messages)

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
