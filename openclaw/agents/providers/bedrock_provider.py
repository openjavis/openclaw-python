"""
AWS Bedrock provider implementation
"""

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

try:
    import boto3

    BEDROCK_AVAILABLE = True
except ImportError:
    BEDROCK_AVAILABLE = False

from .base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class BedrockProvider(LLMProvider):
    """
    AWS Bedrock provider

    Supports models from:
    - Anthropic Claude on Bedrock
    - Meta Llama
    - AI21 Jurassic
    - Cohere Command
    - Amazon Titan

    Example:
        provider = BedrockProvider(
            "anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1"
        )
    """

    def __init__(self, model: str, region: str | None = None, **kwargs):
        if not BEDROCK_AVAILABLE:
            raise ImportError("boto3 is required for Bedrock. Install with: uv add boto3")

        super().__init__(model, **kwargs)
        self.region = region or os.getenv("AWS_REGION", "us-east-1")

    @property
    def provider_name(self) -> str:
        return "bedrock"

    @property
    def supports_streaming(self) -> bool:
        # Bedrock streaming support varies by model
        return "anthropic" in self.model or "claude" in self.model

    def get_client(self) -> Any:
        """Get Bedrock runtime client"""
        if self._client is None:
            self._client = boto3.client(service_name="bedrock-runtime", region_name=self.region)
        return self._client

    def _format_messages_for_bedrock(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, list[dict]]:
        """Format messages for Bedrock"""
        system = None
        bedrock_messages = []

        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                bedrock_messages.append({"role": msg.role, "content": [{"text": msg.content}]})

        return system, bedrock_messages

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """Stream responses from Bedrock"""
        client = self.get_client()

        # Format messages
        system, bedrock_messages = self._format_messages_for_bedrock(messages)

        try:
            # Build request
            request_body = {
                "messages": bedrock_messages,
                "max_tokens": max_tokens,
                "anthropic_version": "bedrock-2023-05-31",
            }

            if system:
                request_body["system"] = system

            if tools:
                request_body["tools"] = tools

            # Invoke with streaming
            response = client.invoke_model_with_response_stream(
                modelId=self.model, body=json.dumps(request_body)
            )

            # Process stream
            for event in response.get("body"):
                chunk = json.loads(event["chunk"]["bytes"])

                if chunk.get("type") == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if "text" in delta:
                        yield LLMResponse(type="text_delta", content=delta["text"])

                elif chunk.get("type") == "message_stop":
                    yield LLMResponse(type="done", content=None, finish_reason="stop")

        except Exception as e:
            logger.error(f"Bedrock streaming error: {e}")
            yield LLMResponse(type="error", content=str(e))
