"""Enhanced event system matching pi-mono's granular events

This module provides a comprehensive event system for agent execution,
including events for messages, tool calls, thinking, and more.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal

from ..events import Event as BaseEvent
from ..events import EventType as BaseEventType


class AgentEventType(str, Enum):
    """Agent event types matching pi-mono"""
    
    # Agent lifecycle
    AGENT_START = "agent_start"
    AGENT_END = "agent_end"
    
    # Turn lifecycle
    TURN_START = "turn_start"
    TURN_END = "turn_end"
    
    # Message lifecycle
    MESSAGE_START = "message_start"
    MESSAGE_UPDATE = "message_update"
    MESSAGE_END = "message_end"
    
    # Tool execution
    TOOL_EXECUTION_START = "tool_execution_start"
    TOOL_EXECUTION_UPDATE = "tool_execution_update"
    TOOL_EXECUTION_END = "tool_execution_end"
    
    # Thinking (reasoning)
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_END = "thinking_end"
    
    # Text streaming
    TEXT_DELTA = "text_delta"
    
    # Tool calls
    TOOLCALL_START = "toolcall_start"
    TOOLCALL_DELTA = "toolcall_delta"
    TOOLCALL_END = "toolcall_end"
    
    # Errors
    ERROR = "error"


@dataclass
class AgentEvent:
    """Base agent event"""
    
    type: AgentEventType
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStartEvent(AgentEvent):
    """Agent started processing"""
    
    type: AgentEventType = field(default=AgentEventType.AGENT_START, init=False)
    
    def __init__(self, model: str, **kwargs):
        super().__init__(type=AgentEventType.AGENT_START)
        self.payload = {"model": model, **kwargs}


@dataclass
class AgentEndEvent(AgentEvent):
    """Agent finished processing"""
    
    type: AgentEventType = field(default=AgentEventType.AGENT_END, init=False)
    
    def __init__(self, reason: str = "completed", **kwargs):
        super().__init__(type=AgentEventType.AGENT_END)
        self.payload = {"reason": reason, **kwargs}


@dataclass
class TurnStartEvent(AgentEvent):
    """Turn started"""
    
    type: AgentEventType = field(default=AgentEventType.TURN_START, init=False)
    
    def __init__(self, turn_number: int, **kwargs):
        super().__init__(type=AgentEventType.TURN_START)
        self.payload = {"turn_number": turn_number, **kwargs}


@dataclass
class TurnEndEvent(AgentEvent):
    """Turn ended"""
    
    type: AgentEventType = field(default=AgentEventType.TURN_END, init=False)
    
    def __init__(self, turn_number: int, has_tool_calls: bool = False, **kwargs):
        super().__init__(type=AgentEventType.TURN_END)
        self.payload = {
            "turn_number": turn_number,
            "has_tool_calls": has_tool_calls,
            **kwargs
        }


@dataclass
class MessageStartEvent(AgentEvent):
    """Message started"""
    
    type: AgentEventType = field(default=AgentEventType.MESSAGE_START, init=False)
    
    def __init__(self, role: Literal["user", "assistant", "system", "toolResult"], 
                 message_id: str | None = None, **kwargs):
        super().__init__(type=AgentEventType.MESSAGE_START)
        self.payload = {"role": role, "message_id": message_id, **kwargs}


@dataclass
class MessageUpdateEvent(AgentEvent):
    """Message updated (streaming)"""
    
    type: AgentEventType = field(default=AgentEventType.MESSAGE_UPDATE, init=False)
    
    def __init__(self, role: str, content: str = "", partial: dict[str, Any] | None = None, **kwargs):
        super().__init__(type=AgentEventType.MESSAGE_UPDATE)
        self.payload = {
            "role": role,
            "content": content,
            "partial": partial or {},
            **kwargs
        }


@dataclass
class MessageEndEvent(AgentEvent):
    """Message ended"""
    
    type: AgentEventType = field(default=AgentEventType.MESSAGE_END, init=False)
    
    def __init__(self, role: str, content: str = "", message_id: str | None = None, **kwargs):
        super().__init__(type=AgentEventType.MESSAGE_END)
        self.payload = {
            "role": role,
            "content": content,
            "message_id": message_id,
            **kwargs
        }


@dataclass
class ToolExecutionStartEvent(AgentEvent):
    """Tool execution started"""
    
    type: AgentEventType = field(default=AgentEventType.TOOL_EXECUTION_START, init=False)
    
    def __init__(self, tool_name: str, tool_call_id: str, params: dict[str, Any], **kwargs):
        super().__init__(type=AgentEventType.TOOL_EXECUTION_START)
        self.payload = {
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "params": params,
            **kwargs
        }


@dataclass
class ToolExecutionUpdateEvent(AgentEvent):
    """Tool execution progress update"""
    
    type: AgentEventType = field(default=AgentEventType.TOOL_EXECUTION_UPDATE, init=False)
    
    def __init__(self, tool_call_id: str, progress: str, **kwargs):
        super().__init__(type=AgentEventType.TOOL_EXECUTION_UPDATE)
        self.payload = {
            "tool_call_id": tool_call_id,
            "progress": progress,
            **kwargs
        }


@dataclass
class ToolExecutionEndEvent(AgentEvent):
    """Tool execution ended"""
    
    type: AgentEventType = field(default=AgentEventType.TOOL_EXECUTION_END, init=False)
    
    def __init__(self, tool_call_id: str, success: bool, result: Any = None, 
                 error: str | None = None, **kwargs):
        super().__init__(type=AgentEventType.TOOL_EXECUTION_END)
        self.payload = {
            "tool_call_id": tool_call_id,
            "success": success,
            "result": result,
            "error": error,
            **kwargs
        }


@dataclass
class ThinkingStartEvent(AgentEvent):
    """Thinking/reasoning started"""
    
    type: AgentEventType = field(default=AgentEventType.THINKING_START, init=False)


@dataclass
class ThinkingDeltaEvent(AgentEvent):
    """Thinking/reasoning delta"""
    
    type: AgentEventType = field(default=AgentEventType.THINKING_DELTA, init=False)
    
    def __init__(self, delta: str, **kwargs):
        super().__init__(type=AgentEventType.THINKING_DELTA)
        self.payload = {"delta": delta, **kwargs}


@dataclass
class ThinkingEndEvent(AgentEvent):
    """Thinking/reasoning ended"""
    
    type: AgentEventType = field(default=AgentEventType.THINKING_END, init=False)
    
    def __init__(self, thinking: str, **kwargs):
        super().__init__(type=AgentEventType.THINKING_END)
        self.payload = {"thinking": thinking, **kwargs}


@dataclass
class TextDeltaEvent(AgentEvent):
    """Text delta (streaming)"""
    
    type: AgentEventType = field(default=AgentEventType.TEXT_DELTA, init=False)
    
    def __init__(self, delta: str, **kwargs):
        super().__init__(type=AgentEventType.TEXT_DELTA)
        self.payload = {"delta": delta, **kwargs}


@dataclass
class ToolCallStartEvent(AgentEvent):
    """Tool call started in stream"""
    
    type: AgentEventType = field(default=AgentEventType.TOOLCALL_START, init=False)
    
    def __init__(self, tool_call_id: str, tool_name: str, **kwargs):
        super().__init__(type=AgentEventType.TOOLCALL_START)
        self.payload = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            **kwargs
        }


@dataclass
class ToolCallDeltaEvent(AgentEvent):
    """Tool call argument delta"""
    
    type: AgentEventType = field(default=AgentEventType.TOOLCALL_DELTA, init=False)
    
    def __init__(self, tool_call_id: str, delta: str, **kwargs):
        super().__init__(type=AgentEventType.TOOLCALL_DELTA)
        self.payload = {
            "tool_call_id": tool_call_id,
            "delta": delta,
            **kwargs
        }


@dataclass
class ToolCallEndEvent(AgentEvent):
    """Tool call ended in stream"""
    
    type: AgentEventType = field(default=AgentEventType.TOOLCALL_END, init=False)
    
    def __init__(self, tool_call_id: str, tool_name: str, params: dict[str, Any], **kwargs):
        super().__init__(type=AgentEventType.TOOLCALL_END)
        self.payload = {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "params": params,
            **kwargs
        }


@dataclass
class ErrorEvent(AgentEvent):
    """Error occurred"""
    
    type: AgentEventType = field(default=AgentEventType.ERROR, init=False)
    
    def __init__(self, error: str, error_type: str | None = None, **kwargs):
        super().__init__(type=AgentEventType.ERROR)
        self.payload = {
            "error": error,
            "error_type": error_type,
            **kwargs
        }


class EventEmitter:
    """Event emitter for agent events"""
    
    def __init__(self):
        self._listeners: dict[AgentEventType | str, list[Callable]] = {}
        self._async_listeners: dict[AgentEventType | str, list[Callable]] = {}
    
    def on(self, event_type: AgentEventType | str, callback: Callable) -> None:
        """Register event listener"""
        if asyncio.iscoroutinefunction(callback):
            if event_type not in self._async_listeners:
                self._async_listeners[event_type] = []
            self._async_listeners[event_type].append(callback)
        else:
            if event_type not in self._listeners:
                self._listeners[event_type] = []
            self._listeners[event_type].append(callback)
    
    def off(self, event_type: AgentEventType | str, callback: Callable) -> None:
        """Unregister event listener"""
        if asyncio.iscoroutinefunction(callback):
            if event_type in self._async_listeners:
                self._async_listeners[event_type].remove(callback)
        else:
            if event_type in self._listeners:
                self._listeners[event_type].remove(callback)
    
    async def emit(self, event: AgentEvent) -> None:
        """Emit event to all listeners"""
        event_type = event.type
        
        # Call sync listeners
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # Don't let listener errors break event emission
                    import logging
                    logging.getLogger(__name__).error(
                        f"Error in event listener for {event_type}: {e}",
                        exc_info=True
                    )
        
        # Call async listeners
        if event_type in self._async_listeners:
            for callback in self._async_listeners[event_type]:
                try:
                    await callback(event)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(
                        f"Error in async event listener for {event_type}: {e}",
                        exc_info=True
                    )
    
    def once(self, event_type: AgentEventType | str, callback: Callable) -> None:
        """Register one-time event listener"""
        def wrapper(event: AgentEvent):
            self.off(event_type, wrapper)
            callback(event)
        
        self.on(event_type, wrapper)


class AgentEventStream:
    """Async iterator for agent events"""
    
    def __init__(self, queue_size: int = 1000):
        self._queue: asyncio.Queue[AgentEvent | None] = asyncio.Queue(maxsize=queue_size)
        self._closed = False
    
    async def put(self, event: AgentEvent) -> None:
        """Add event to stream"""
        if not self._closed:
            await self._queue.put(event)
    
    async def close(self) -> None:
        """Close the stream"""
        self._closed = True
        await self._queue.put(None)  # Sentinel
    
    def __aiter__(self) -> AsyncIterator[AgentEvent]:
        return self
    
    async def __anext__(self) -> AgentEvent:
        event = await self._queue.get()
        if event is None:
            raise StopAsyncIteration
        return event


# Backwards compatibility with existing Event system
AgentEvent.__bases__ = (BaseEvent,)
