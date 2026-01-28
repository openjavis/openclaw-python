"""Agent runtime with LLM integration"""

import asyncio
from typing import Any, AsyncIterator, Optional
import logging

from .session import Session
from .tools.base import AgentTool, ToolResult
from .context import ContextManager, ContextWindow
from .errors import (
    AgentError,
    ContextOverflowError,
    RateLimitError,
    ErrorRecovery,
    classify_error,
    is_retryable_error,
    format_error_message
)

logger = logging.getLogger(__name__)


class AgentEvent:
    """Event emitted during agent execution"""

    def __init__(self, event_type: str, data: Any):
        self.type = event_type
        self.data = data


class AgentRuntime:
    """Agent runtime that executes LLM turns with tools"""

    def __init__(
        self,
        model: str = "anthropic/claude-opus-4-5-20250514",
        api_key: Optional[str] = None,
        max_retries: int = 3,
        enable_context_management: bool = True
    ):
        self.model = model
        self.api_key = api_key
        self.max_retries = max_retries
        self.enable_context_management = enable_context_management
        self._client: Optional[Any] = None
        
        # Initialize context manager
        if enable_context_management:
            model_name = model.split("/")[1] if "/" in model else model
            self.context_manager = ContextManager(model_name)
        else:
            self.context_manager = None

    def _get_client(self) -> Any:
        """Get LLM client (lazy initialization)"""
        if self._client is not None:
            return self._client

        provider = self.model.split("/")[0] if "/" in self.model else "anthropic"

        if provider == "anthropic":
            import anthropic
            import os
            api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        elif provider == "openai":
            import openai
            import os
            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            self._client = openai.AsyncOpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unsupported model provider: {provider}")

        return self._client

    def _format_tools_for_api(self, tools: list[AgentTool]) -> list[dict[str, Any]]:
        """Format tools for API"""
        formatted = []
        for tool in tools:
            formatted.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.get_schema()
            })
        return formatted

    async def run_turn(
        self,
        session: Session,
        message: str,
        tools: Optional[list[AgentTool]] = None,
        max_tokens: int = 4096
    ) -> AsyncIterator[AgentEvent]:
        """Run an agent turn with streaming"""
        if tools is None:
            tools = []

        # Add user message to session
        session.add_user_message(message)

        # Build messages for API
        messages = []
        for msg in session.get_messages():
            if msg.role == "tool":
                # Tool result message
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content
                    }]
                })
            else:
                # Regular message
                content = msg.content
                if msg.tool_calls:
                    # Message with tool calls
                    messages.append({
                        "role": msg.role,
                        "content": [
                            {"type": "text", "text": content} if content else None,
                            *[{
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": tc["name"],
                                "input": tc["arguments"]
                            } for tc in msg.tool_calls]
                        ]
                    })
                    # Remove None values
                    messages[-1]["content"] = [c for c in messages[-1]["content"] if c is not None]
                else:
                    messages.append({
                        "role": msg.role,
                        "content": content
                    })

        yield AgentEvent("lifecycle", {"phase": "start"})

        try:
            provider = self.model.split("/")[0] if "/" in self.model else "anthropic"
            model_name = self.model.split("/")[1] if "/" in self.model else self.model

            if provider == "anthropic":
                async for event in self._run_anthropic(messages, tools, model_name, max_tokens):
                    yield event
            elif provider == "openai":
                async for event in self._run_openai(messages, tools, model_name, max_tokens):
                    yield event

            yield AgentEvent("lifecycle", {"phase": "end"})

        except Exception as e:
            logger.error(f"Agent turn error: {e}", exc_info=True)
            yield AgentEvent("lifecycle", {"phase": "error", "error": str(e)})
            raise

    async def _run_anthropic(
        self,
        messages: list[dict[str, Any]],
        tools: list[AgentTool],
        model: str,
        max_tokens: int
    ) -> AsyncIterator[AgentEvent]:
        """Run with Anthropic API"""
        client = self._get_client()

        # Format tools
        tools_param = self._format_tools_for_api(tools) if tools else None

        # Stream response
        accumulated_text = ""
        tool_calls = []

        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            tools=tools_param
        ) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_start":
                        if hasattr(event, "content_block") and event.content_block.type == "text":
                            yield AgentEvent("assistant", {"delta": {"type": "text_delta", "text": ""}})
                    elif event.type == "content_block_delta":
                        if hasattr(event, "delta"):
                            if event.delta.type == "text_delta":
                                text = event.delta.text
                                accumulated_text += text
                                yield AgentEvent("assistant", {"delta": {"type": "text_delta", "text": text}})
                    elif event.type == "content_block_stop":
                        pass

            # Get final message
            final_message = await stream.get_final_message()

            # Check for tool calls
            for block in final_message.content:
                if block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input
                    })

                    # Execute tool
                    tool = next((t for t in tools if t.name == block.name), None)
                    if tool:
                        yield AgentEvent("tool", {
                            "toolCallId": block.id,
                            "toolName": block.name,
                            "phase": "start"
                        })

                        try:
                            result = await tool.execute(block.input)
                            yield AgentEvent("tool", {
                                "toolCallId": block.id,
                                "toolName": block.name,
                                "phase": "end",
                                "result": result.content
                            })
                        except Exception as e:
                            yield AgentEvent("tool", {
                                "toolCallId": block.id,
                                "toolName": block.name,
                                "phase": "error",
                                "error": str(e)
                            })

        # Save assistant message
        # Note: Session saving handled by caller

    async def _run_openai(
        self,
        messages: list[dict[str, Any]],
        tools: list[AgentTool],
        model: str,
        max_tokens: int
    ) -> AsyncIterator[AgentEvent]:
        """Run with OpenAI API"""
        client = self._get_client()

        # Format tools for OpenAI
        tools_param = None
        if tools:
            tools_param = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.get_schema()
                }
            } for tool in tools]

        # Stream response
        accumulated_text = ""
        tool_calls = []

        stream = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            tools=tools_param,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices:
                choice = chunk.choices[0]
                if choice.delta.content:
                    text = choice.delta.content
                    accumulated_text += text
                    yield AgentEvent("assistant", {"delta": {"type": "text_delta", "text": text}})

                # Handle tool calls
                if choice.delta.tool_calls:
                    for tool_call in choice.delta.tool_calls:
                        # TODO: Accumulate tool call data and execute
                        pass
