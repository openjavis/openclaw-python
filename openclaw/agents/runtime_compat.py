"""
Compatibility adapter for legacy AgentRuntime interface.

This module provides backward compatibility while using the new Agent v2 implementation.
Existing code using AgentRuntime/MultiProviderRuntime can continue to work
with minimal changes during the migration period.

Usage:
    # Old code (still works):
    from openclaw.agents.runtime import AgentRuntime
    runtime = AgentRuntime(provider_name="openai", model_name="gpt-4")
    
    # New code (recommended):
    from openclaw.agents import Agent
    agent = Agent(model="openai/gpt-4", ...)
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from .agent import Agent
from .events import AgentEvent, AgentEventType
from .queues import AgentSession
from .thinking import ThinkingLevel
from .types import AgentMessage, AssistantMessage, TextContent, UserMessage

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Compatibility adapter for legacy AgentRuntime interface.
    
    Wraps the new Agent v2 implementation to provide backward compatibility.
    """
    
    def __init__(
        self,
        provider_name: str,
        model_name: str,
        system_prompt: str = "",
        tools: list[Any] | None = None,
        thinking_level: str = "off",
        **kwargs
    ):
        """
        Initialize runtime with legacy parameters.
        
        Args:
            provider_name: Provider name (openai, anthropic, etc.)
            model_name: Model name (gpt-4, claude-3-sonnet, etc.)
            system_prompt: System prompt for agent
            tools: List of tools
            thinking_level: Thinking level (off, minimal, low, medium, high, xhigh)
            **kwargs: Additional configuration
        """
        # Convert to new format
        model_str = f"{provider_name}/{model_name}"
        
        # Map thinking level string to enum
        thinking_map = {
            "off": ThinkingLevel.OFF,
            "minimal": ThinkingLevel.MINIMAL,
            "low": ThinkingLevel.LOW,
            "medium": ThinkingLevel.MEDIUM,
            "high": ThinkingLevel.HIGH,
            "xhigh": ThinkingLevel.XHIGH,
        }
        thinking_enum = thinking_map.get(thinking_level.lower(), ThinkingLevel.OFF)
        
        # Create new agent
        try:
            self._agent = Agent(
                system_prompt=system_prompt,
                model=model_str,
                tools=tools or [],
                thinking_level=thinking_enum,
            )
        except:
            # Fallback if Agent not available
            logger.warning("Agent not available")
            self._agent = None
        
        self._session = AgentSession(self._agent) if self._agent else None
        self._provider_name = provider_name
        self._model_name = model_name
        self._system_prompt = system_prompt
        self._tools = tools or []
    
    async def run_turn(
        self,
        session: Any,
        message: str | list[dict],
        tools: list[Any] | None = None,
        **kwargs
    ) -> AsyncIterator[dict[str, Any]]:
        """
        Run a single turn (legacy interface).
        
        Args:
            session: Session object (ignored, using internal session)
            message: User message (string or message array)
            tools: Tools for this turn (overrides init tools)
            **kwargs: Additional options
            
        Yields:
            Legacy-format events
        """
        # Convert message to new format
        if isinstance(message, str):
            user_msg = UserMessage(content=message)
        elif isinstance(message, list):
            # Handle complex message format
            user_msg = UserMessage(content=str(message))
        else:
            user_msg = UserMessage(content=str(message))
        
        # Update tools if provided
        if tools is not None:
            self._agent._tools = tools
        
        # Run agent
        if self._session:
            async for event in self._session.prompt([user_msg]):
                # Translate to legacy format
                legacy_event = self._translate_event_to_legacy(event)
                if legacy_event:
                    yield legacy_event
        else:
            # Fallback: yield error
            yield {
                "type": "error",
                "error": "Agent not initialized"
            }
    
    async def prompt(
        self,
        messages: list[AgentMessage],
        **kwargs
    ) -> AsyncIterator[AgentEvent]:
        """
        Direct prompt method using new interface.
        
        Args:
            messages: List of agent messages
            **kwargs: Additional options
            
        Yields:
            Agent events
        """
        if self._session:
            async for event in self._session.prompt(messages):
                yield event
    
    def _translate_event_to_legacy(self, event: AgentEvent) -> dict[str, Any] | None:
        """
        Translate new Agent v2 event to legacy format.
        
        Args:
            event: New agent event
            
        Returns:
            Legacy event dict or None if not translatable
        """
        event_type = event.type
        payload = event.payload
        
        # Map event types to legacy format
        if event_type == AgentEventType.AGENT_START:
            return {
                "type": "agent_start",
                "model": payload.get("model", ""),
            }
        
        elif event_type == AgentEventType.AGENT_END:
            return {
                "type": "agent_end",
                "reason": payload.get("reason", "completed"),
                "messages": payload.get("messages", []),
            }
        
        elif event_type == AgentEventType.MESSAGE_START:
            msg = payload.get("message")
            if msg:
                return {
                    "type": "message_start",
                    "role": msg.role,
                }
            return None
        
        elif event_type == AgentEventType.MESSAGE_UPDATE:
            return {
                "type": "message_update",
                "role": payload.get("role", ""),
                "content": payload.get("content", ""),
                "partial": payload.get("partial", {}),
            }
        
        elif event_type == AgentEventType.MESSAGE_END:
            msg = payload.get("message")
            if msg:
                return {
                    "type": "message_end",
                    "role": msg.role,
                    "content": self._extract_message_content(msg),
                }
            return None
        
        elif event_type == AgentEventType.TOOL_EXECUTION_START:
            return {
                "type": "tool_start",
                "tool_name": payload.get("toolName", ""),
                "tool_call_id": payload.get("toolCallId", ""),
                "args": payload.get("args", {}),
            }
        
        elif event_type == AgentEventType.TOOL_EXECUTION_END:
            result = payload.get("result")
            return {
                "type": "tool_end",
                "tool_name": payload.get("toolName", ""),
                "tool_call_id": payload.get("toolCallId", ""),
                "result": result,
                "is_error": payload.get("isError", False),
            }
        
        elif event_type == AgentEventType.TURN_START:
            return {
                "type": "turn_start",
                "turn_number": payload.get("turn_number", 0),
            }
        
        elif event_type == AgentEventType.TURN_END:
            return {
                "type": "turn_end",
                "turn_number": payload.get("turn_number", 0),
                "message": payload.get("message"),
                "tool_results": payload.get("toolResults", []),
            }
        
        # Skip other event types
        return None
    
    def _extract_message_content(self, message: AgentMessage) -> str:
        """
        Extract text content from message.
        
        Args:
            message: Agent message
            
        Returns:
            Text content as string
        """
        if isinstance(message, UserMessage):
            if isinstance(message.content, str):
                return message.content
            elif isinstance(message.content, list):
                # Extract text from content array
                texts = []
                for item in message.content:
                    if isinstance(item, TextContent):
                        texts.append(item.text)
                    elif isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                return "".join(texts)
        
        elif isinstance(message, AssistantMessage):
            # Extract text from content array
            texts = []
            for item in message.content:
                if isinstance(item, TextContent):
                    texts.append(item.text)
                elif isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return "".join(texts)
        
        return str(message.content)


# Alias for backward compatibility
MultiProviderRuntime = AgentRuntime


__all__ = [
    "AgentRuntime",
    "MultiProviderRuntime",
]
