"""
Base LLM Provider interface
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMMessage:
    """Message for LLM"""

    role: str
    content: Any
    images: list[str] | None = None  # List of image URLs or file paths


@dataclass
class LLMResponse:
    """Response from LLM"""

    type: str
    content: Any
    tool_calls: list[dict] | None = None
    finish_reason: str | None = None
    usage: dict | None = None


class LLMProvider(ABC):
    """
    Base class for LLM providers

    Supports: Anthropic, OpenAI, Google Gemini, AWS Bedrock, Ollama, etc.
    """

    def __init__(
        self, model: str, api_key: str | None = None, base_url: str | None = None, **kwargs
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.extra_params = kwargs
        self._client: Any | None = None

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """
        Stream responses from the LLM

        Args:
            messages: List of messages
            tools: Optional tool definitions
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            LLMResponse objects
        """
        pass

    @abstractmethod
    def get_client(self) -> Any:
        """Get or create the provider client"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'anthropic', 'openai', 'gemini')"""
        pass

    @property
    def supports_system_message(self) -> bool:
        """Whether this provider supports system messages"""
        return True

    @property
    def supports_tool_calling(self) -> bool:
        """Whether this provider supports tool/function calling"""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming"""
        return True

    def format_tools(self, tools: list[dict]) -> Any:
        """
        Format tools for this provider

        Override if provider needs special tool format
        """
        return tools
