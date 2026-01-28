"""
Enhanced Agent runtime with multi-provider support
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from .context import ContextManager
from .errors import classify_error, format_error_message, is_retryable_error
from .providers import (
    AnthropicProvider,
    BedrockProvider,
    GeminiProvider,
    LLMMessage,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)
from .session import Session
from .tools.base import AgentTool

logger = logging.getLogger(__name__)


class AgentEvent:
    """Event emitted during agent execution"""

    def __init__(self, event_type: str, data: Any):
        self.type = event_type
        self.data = data


class MultiProviderRuntime:
    """
    Enhanced Agent runtime with support for multiple LLM providers

    Supported providers:
    - anthropic: Claude models
    - openai: GPT models
    - gemini: Google Gemini
    - bedrock: AWS Bedrock
    - ollama: Local models
    - openai-compatible: Any OpenAI-compatible API

    Model format: "provider/model" or just "model" (defaults to anthropic)

    Examples:
        # Anthropic
        runtime = MultiProviderRuntime("anthropic/claude-opus-4-5")

        # OpenAI
        runtime = MultiProviderRuntime("openai/gpt-4")

        # Google Gemini
        runtime = MultiProviderRuntime("gemini/gemini-pro")

        # AWS Bedrock
        runtime = MultiProviderRuntime("bedrock/anthropic.claude-3-sonnet")

        # Ollama (local)
        runtime = MultiProviderRuntime("ollama/llama3")

        # OpenAI-compatible (custom base URL)
        runtime = MultiProviderRuntime(
            "lmstudio/model-name",
            base_url="http://localhost:1234/v1"
        )
    """

    def __init__(
        self,
        model: str = "anthropic/claude-opus-4-5-20250514",
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
        enable_context_management: bool = True,
        **kwargs,
    ):
        self.model_str = model
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.enable_context_management = enable_context_management
        self.extra_params = kwargs

        # Parse provider and model
        self.provider_name, self.model_name = self._parse_model(model)

        # Initialize provider
        self.provider = self._create_provider()

        # Initialize context manager
        if enable_context_management:
            self.context_manager = ContextManager(self.model_name)
        else:
            self.context_manager = None

    def _parse_model(self, model: str) -> tuple[str, str]:
        """
        Parse model string into provider and model name

        Examples:
            "anthropic/claude-opus" -> ("anthropic", "claude-opus")
            "gemini/gemini-pro" -> ("gemini", "gemini-pro")
            "claude-opus" -> ("anthropic", "claude-opus")  # default
        """
        if "/" in model:
            parts = model.split("/", 1)
            return parts[0], parts[1]
        else:
            # Default to anthropic
            return "anthropic", model

    def _create_provider(self) -> LLMProvider:
        """Create appropriate provider based on provider name"""
        provider_name = self.provider_name.lower()

        # Common parameters
        kwargs = {
            "model": self.model_name,
            "api_key": self.api_key,
            "base_url": self.base_url,
            **self.extra_params,
        }

        # Create provider
        if provider_name == "anthropic":
            return AnthropicProvider(**kwargs)

        elif provider_name == "openai":
            return OpenAIProvider(**kwargs)

        elif provider_name in ("gemini", "google", "google-gemini"):
            return GeminiProvider(**kwargs)

        elif provider_name in ("bedrock", "aws-bedrock"):
            return BedrockProvider(**kwargs)

        elif provider_name == "ollama":
            return OllamaProvider(**kwargs)

        elif provider_name in ("lmstudio", "openai-compatible", "custom"):
            # OpenAI-compatible with custom base URL
            return OpenAIProvider(**kwargs)

        else:
            # Unknown provider, try OpenAI-compatible
            logger.warning(f"Unknown provider '{provider_name}', trying OpenAI-compatible mode")
            return OpenAIProvider(**kwargs)

    async def run_turn(
        self,
        session: Session,
        message: str,
        tools: list[AgentTool] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[AgentEvent]:
        """
        Run an agent turn with the configured provider

        Args:
            session: Session to use
            message: User message
            tools: Optional list of tools
            max_tokens: Maximum tokens to generate

        Yields:
            AgentEvent objects
        """
        if tools is None:
            tools = []

        # Add user message
        session.add_user_message(message)

        # Check context window
        if self.context_manager and self.enable_context_management:
            messages_for_api = session.get_messages_for_api()
            current_tokens = self.context_manager.estimate_messages_tokens(messages_for_api)
            window = self.context_manager.check_context(current_tokens)

            if window.should_compress:
                logger.info(
                    f"Context at {window.used_tokens}/{window.total_tokens} tokens, pruning"
                )
                if len(session.messages) > 25:
                    system_msgs = [m for m in session.messages if m.role == "system"]
                    recent_msgs = session.messages[-20:]
                    session.messages = system_msgs + recent_msgs

        yield AgentEvent("lifecycle", {"phase": "start"})

        # Execute with retry logic
        retry_count = 0

        while retry_count <= self.max_retries:
            try:
                # Convert session messages to LLM format
                llm_messages = []
                for msg in session.get_messages():
                    llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

                # Format tools for provider
                tools_param = None
                if tools:
                    tools_param = [
                        {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": tool.parameters,
                            },
                        }
                        for tool in tools
                    ]

                # Stream from provider
                accumulated_text = ""
                tool_calls = []

                async for response in self.provider.stream(
                    messages=llm_messages, tools=tools_param, max_tokens=max_tokens
                ):
                    if response.type == "text_delta":
                        accumulated_text += response.content
                        yield AgentEvent(
                            "assistant", {"delta": {"type": "text_delta", "text": response.content}}
                        )

                    elif response.type == "tool_call":
                        tool_calls = response.tool_calls or []

                        # Execute tools
                        for tc in tool_calls:
                            tool = next((t for t in tools if t.name == tc["name"]), None)
                            if tool:
                                yield AgentEvent(
                                    "tool_use", {"tool": tc["name"], "input": tc["arguments"]}
                                )

                                # Execute tool
                                result = await tool.execute(tc["arguments"])

                                yield AgentEvent(
                                    "tool_result",
                                    {
                                        "tool": tc["name"],
                                        "result": result.output if result else None,
                                    },
                                )

                                # Add tool result to session
                                session.add_tool_result(
                                    tool_call_id=tc["id"],
                                    tool_name=tc["name"],
                                    result=result.output if result else "Error",
                                )

                    elif response.type == "done":
                        # Save assistant message
                        if accumulated_text:
                            session.add_assistant_message(accumulated_text, tool_calls)

                        break

                    elif response.type == "error":
                        raise Exception(response.content)

                # Success, exit retry loop
                yield AgentEvent("lifecycle", {"phase": "end"})
                return

            except Exception as e:
                # Check if retryable
                if not is_retryable_error(e):
                    logger.error(f"Non-retryable error: {format_error_message(e)}")
                    yield AgentEvent(
                        "error",
                        {"message": format_error_message(e), "category": classify_error(e).value},
                    )
                    yield AgentEvent("lifecycle", {"phase": "end"})
                    return

                if retry_count >= self.max_retries:
                    logger.error(f"Max retries reached: {format_error_message(e)}")
                    yield AgentEvent(
                        "error",
                        {
                            "message": f"Max retries exceeded: {format_error_message(e)}",
                            "category": classify_error(e).value,
                        },
                    )
                    yield AgentEvent("lifecycle", {"phase": "end"})
                    return

                # Retry with exponential backoff
                retry_count += 1
                delay = min(2 ** (retry_count - 1), 30)
                logger.warning(f"Retry {retry_count}/{self.max_retries} after {delay}s: {e}")

                yield AgentEvent(
                    "retry",
                    {
                        "attempt": retry_count,
                        "max_retries": self.max_retries,
                        "delay": delay,
                        "error": str(e),
                    },
                )

                await asyncio.sleep(delay)


# Alias for backward compatibility
AgentRuntime = MultiProviderRuntime
