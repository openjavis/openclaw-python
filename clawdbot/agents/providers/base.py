"""
Base LLM Provider interface
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMMessage:
    """Message for LLM"""
    role: str
    content: Any


@dataclass
class LLMResponse:
    """Response from LLM"""
    type: str
    content: Any
    tool_calls: Optional[list[dict]] = None
    finish_reason: Optional[str] = None
    usage: Optional[dict] = None


class LLMProvider(ABC):
    """
    Base class for LLM providers
    
    Supports: Anthropic, OpenAI, Google Gemini, AWS Bedrock, Ollama, etc.
    """
    
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.extra_params = kwargs
        self._client: Optional[Any] = None
    
    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        **kwargs
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
