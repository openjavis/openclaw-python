"""
Event Stream implementation aligned with pi-mono

Provides typed event streaming with result extraction, matching TypeScript EventStream<TEvent, TResult>
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

TEvent = TypeVar('TEvent')
TResult = TypeVar('TResult')


class EventStream(Generic[TEvent, TResult]):
    """
    Event stream with result extraction - aligned with pi-mono EventStream<TEvent, TResult>
    
    Provides:
    - Async iteration over events
    - Result extraction when stream completes
    - Event pushing and stream termination
    - Type safety through generics
    
    Example:
        # Create stream that completes on "done" events
        stream = EventStream(
            is_done=lambda e: e.type == "done",
            extract_result=lambda e: e.messages if hasattr(e, 'messages') else []
        )
        
        # Push events
        stream.push({"type": "start"})
        stream.push({"type": "text", "content": "Hello"})
        stream.push({"type": "done", "messages": [...]})
        
        # Iterate over events
        async for event in stream:
            print(event)
        
        # Get final result
        result = await stream.get_result()
    """
    
    def __init__(
        self,
        is_done: Callable[[TEvent], bool],
        extract_result: Callable[[TEvent], TResult],
    ):
        """
        Initialize event stream
        
        Args:
            is_done: Function to determine if event completes the stream
            extract_result: Function to extract result from completion event
        """
        self._is_done = is_done
        self._extract_result = extract_result
        self._queue: asyncio.Queue[TEvent | None] = asyncio.Queue()
        self._done = False
        self._result: TResult | None = None
        self._ended = False
    
    def push(self, event: TEvent) -> None:
        """
        Push an event to the stream
        
        Args:
            event: Event to push
        """
        if self._ended:
            logger.warning("Attempted to push event to ended stream")
            return
        
        # Check if this event completes the stream
        if self._is_done(event):
            self._done = True
            self._result = self._extract_result(event)
        
        # Add to queue
        self._queue.put_nowait(event)
    
    def end(self, result: TResult | None = None) -> None:
        """
        End the stream
        
        Args:
            result: Optional result to set (overrides extracted result)
        """
        if self._ended:
            return
        
        self._ended = True
        if result is not None:
            self._result = result
        
        # Signal end by pushing None
        self._queue.put_nowait(None)
    
    async def __aiter__(self) -> AsyncIterator[TEvent]:
        """
        Async iterator over events in stream
        
        Yields events until stream ends (None received from queue)
        """
        while True:
            event = await self._queue.get()
            
            # None signals end of stream
            if event is None:
                break
            
            yield event
            
            # Check if stream is done after yielding
            if self._done:
                # Wait for end() call or push remaining events
                # Don't break yet - let producer call end()
                pass
    
    async def get_result(self) -> TResult:
        """
        Get final result after consuming all events
        
        This will wait for all events to be consumed and return the extracted result.
        
        Returns:
            Final result extracted from completion event
        """
        # Consume all events
        async for _ in self:
            pass
        
        return self._result
    
    @property
    def is_done(self) -> bool:
        """Check if stream has completed"""
        return self._done
    
    @property
    def is_ended(self) -> bool:
        """Check if stream has been ended"""
        return self._ended


def create_agent_event_stream():
    """
    Create an EventStream for AgentEvent - aligned with pi-mono createAgentStream()
    
    Returns:
        EventStream that completes on agent_end events
    """
    from .events import AgentEndEvent
    
    def is_done(event) -> bool:
        """Check if event is agent_end"""
        if isinstance(event, AgentEndEvent):
            return True
        if isinstance(event, dict) and event.get("type") == "agent_end":
            return True
        return False
    
    def extract_result(event):
        """Extract messages from agent_end event"""
        if isinstance(event, AgentEndEvent):
            return getattr(event, 'messages', [])
        if isinstance(event, dict):
            return event.get("messages", [])
        return []
    
    return EventStream(is_done=is_done, extract_result=extract_result)
