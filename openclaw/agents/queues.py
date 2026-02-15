"""
Message queue system for steering and follow-up messages

This module provides thread-safe message queues for:
- Steering: High-priority messages that interrupt current turn
- Follow-up: Messages queued after current turn completes

Matches Pi Agent's steering and follow-up message handling.
"""
from __future__ import annotations

import asyncio
import threading
from collections import deque
from typing import Generic, TypeVar

from .types import AgentMessage

T = TypeVar("T")


class MessageQueue(Generic[T]):
    """
    Thread-safe message queue.
    
    Provides push/pop operations with thread safety for:
    - Steering messages (interrupt current execution)
    - Follow-up messages (queued for later)
    
    Example:
        ```python
        queue = MessageQueue()
        
        # Producer (can be different thread)
        queue.push(message)
        
        # Consumer (agent loop)
        messages = queue.pop_all()
        for msg in messages:
            process(msg)
        ```
    """
    
    def __init__(self):
        """Initialize empty queue"""
        self._queue: deque[T] = deque()
        self._lock = threading.Lock()
    
    def push(self, item: T) -> None:
        """
        Push item into queue.
        
        Thread-safe operation.
        
        Args:
            item: Item to push
        """
        with self._lock:
            self._queue.append(item)
    
    def pop_all(self) -> list[T]:
        """
        Pop all items from queue.
        
        Thread-safe operation that atomically removes all items.
        
        Returns:
            List of all items (empty list if queue was empty)
        """
        with self._lock:
            items = list(self._queue)
            self._queue.clear()
            return items
    
    def clear(self) -> None:
        """
        Clear all items from queue.
        
        Thread-safe operation.
        """
        with self._lock:
            self._queue.clear()
    
    def is_empty(self) -> bool:
        """
        Check if queue is empty.
        
        Thread-safe operation.
        
        Returns:
            True if queue is empty
        """
        with self._lock:
            return len(self._queue) == 0
    
    def size(self) -> int:
        """
        Get current queue size.
        
        Thread-safe operation.
        
        Returns:
            Number of items in queue
        """
        with self._lock:
            return len(self._queue)
    
    def peek(self) -> T | None:
        """
        Peek at first item without removing.
        
        Thread-safe operation.
        
        Returns:
            First item or None if empty
        """
        with self._lock:
            return self._queue[0] if self._queue else None


class SteeringQueue:
    """
    Steering message queue with priority handling.
    
    Steering messages are high-priority and interrupt current agent turn.
    When steering messages are present:
    - Current tool execution is stopped
    - Remaining tools are skipped
    - Steering messages are injected immediately
    
    Example:
        ```python
        steering = SteeringQueue()
        
        # User sends interrupt message
        steering.push(UserMessage(content="Stop! Do this instead"))
        
        # Agent loop checks and processes
        if steering.has_messages():
            messages = steering.pop_all()
            # Process steering messages immediately
        ```
    """
    
    def __init__(self):
        """Initialize steering queue"""
        self._queue = MessageQueue[AgentMessage]()
    
    def push(self, message: AgentMessage) -> None:
        """
        Push steering message.
        
        Args:
            message: Steering message to push
        """
        self._queue.push(message)
    
    def pop_all(self) -> list[AgentMessage]:
        """
        Pop all steering messages.
        
        Returns:
            All steering messages
        """
        return self._queue.pop_all()
    
    def clear(self) -> None:
        """Clear all steering messages"""
        self._queue.clear()
    
    def has_messages(self) -> bool:
        """
        Check if there are pending steering messages.
        
        Returns:
            True if steering messages are queued
        """
        return not self._queue.is_empty()
    
    async def get_messages(self) -> list[AgentMessage]:
        """
        Async get messages (for AgentLoopConfig callback).
        
        Returns:
            All steering messages
        """
        return self.pop_all()


class FollowUpQueue:
    """
    Follow-up message queue for continuation.
    
    Follow-up messages are processed after current turn completes.
    They allow agent to continue with new context without stopping.
    
    Difference from steering:
    - Follow-up waits for current turn to complete
    - Steering interrupts current turn immediately
    
    Example:
        ```python
        followup = FollowUpQueue()
        
        # Queue message for after current turn
        followup.push(UserMessage(content="Also, tell me about X"))
        
        # Agent loop checks after turn completes
        if followup.has_messages():
            messages = followup.pop_all()
            # Continue with follow-up messages
        ```
    """
    
    def __init__(self):
        """Initialize follow-up queue"""
        self._queue = MessageQueue[AgentMessage]()
    
    def push(self, message: AgentMessage) -> None:
        """
        Push follow-up message.
        
        Args:
            message: Follow-up message to push
        """
        self._queue.push(message)
    
    def pop_all(self) -> list[AgentMessage]:
        """
        Pop all follow-up messages.
        
        Returns:
            All follow-up messages
        """
        return self._queue.pop_all()
    
    def clear(self) -> None:
        """Clear all follow-up messages"""
        self._queue.clear()
    
    def has_messages(self) -> bool:
        """
        Check if there are pending follow-up messages.
        
        Returns:
            True if follow-up messages are queued
        """
        return not self._queue.is_empty()
    
    async def get_messages(self) -> list[AgentMessage]:
        """
        Async get messages (for AgentLoopConfig callback).
        
        Returns:
            All follow-up messages
        """
        return self.pop_all()


class AgentSession:
    """
    High-level agent session with queue management.
    
    Provides convenience methods for:
    - Steering (interrupting current execution)
    - Follow-up (continuing after completion)
    - State management
    
    Example:
        ```python
        from .agent_v2 import Agent
        
        agent = Agent(...)
        session = AgentSession(agent)
        
        # Start agent
        async for event in session.prompt([UserMessage(content="Hello")]):
            print(event)
        
        # User interrupts
        session.steer("Stop! Do something else")
        
        # Or queue for later
        session.follow_up("After this, tell me about X")
        ```
    """
    
    def __init__(self, agent: Any):  # Any to avoid circular import
        """
        Initialize session.
        
        Args:
            agent: Agent instance to manage
        """
        self.agent = agent
        self._steering_queue = SteeringQueue()
        self._followup_queue = FollowUpQueue()
        
        # Wire up queues to agent loop config
        # This will be done when agent runs
    
    def steer(self, message: str | AgentMessage) -> None:
        """
        Add steering message (interrupts current turn).
        
        Steering messages are high-priority and will:
        - Stop current tool execution
        - Skip remaining tools
        - Inject immediately into conversation
        
        Args:
            message: Steering message (string or AgentMessage)
            
        Example:
            ```python
            session.steer("Stop! Search for different information")
            ```
        """
        if isinstance(message, str):
            from .types import UserMessage
            message = UserMessage(content=message)
        
        self._steering_queue.push(message)
    
    def follow_up(self, message: str | AgentMessage) -> None:
        """
        Add follow-up message (queued after current turn).
        
        Follow-up messages wait for current turn to complete,
        then agent continues with the new message.
        
        Args:
            message: Follow-up message (string or AgentMessage)
            
        Example:
            ```python
            session.follow_up("Also, can you explain X?")
            ```
        """
        if isinstance(message, str):
            from .types import UserMessage
            message = UserMessage(content=message)
        
        self._followup_queue.push(message)
    
    def clear_steering(self) -> None:
        """Clear all pending steering messages"""
        self._steering_queue.clear()
    
    def clear_followup(self) -> None:
        """Clear all pending follow-up messages"""
        self._followup_queue.clear()
    
    def has_steering(self) -> bool:
        """Check if steering messages are queued"""
        return self._steering_queue.has_messages()
    
    def has_followup(self) -> bool:
        """Check if follow-up messages are queued"""
        return self._followup_queue.has_messages()
    
    async def _get_steering_messages(self) -> list[AgentMessage]:
        """Callback for agent loop config"""
        return await self._steering_queue.get_messages()
    
    async def _get_followup_messages(self) -> list[AgentMessage]:
        """Callback for agent loop config"""
        return await self._followup_queue.get_messages()
    
    async def prompt(self, messages: list[AgentMessage]) -> Any:
        """
        Start agent with messages and queue callbacks.
        
        Args:
            messages: Initial messages
            
        Yields:
            Agent events
        """
        # Update agent's config to use our queues
        from .agent_loop_v2 import AgentLoopConfig
        
        # This would need to be integrated with agent_v2.Agent
        # to wire up the queue callbacks
        
        async for event in self.agent.prompt(messages):
            yield event
    
    async def continue_agent(self) -> Any:
        """
        Continue agent with queue callbacks.
        
        Yields:
            Agent events
        """
        async for event in self.agent.continue_agent():
            yield event


__all__ = [
    "MessageQueue",
    "SteeringQueue",
    "FollowUpQueue",
    "AgentSession",
]
