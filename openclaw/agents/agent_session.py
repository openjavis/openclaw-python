"""Agent Session - pi-ai style session API

This module provides a high-level session API similar to pi-ai's session.prompt(),
wrapping the tool loop orchestrator for automatic tool execution.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw.agents.runtime import MultiProviderRuntime
    from openclaw.agents.session import Session
    from openclaw.agents.tools.base import SimpleTool

from openclaw.agents.events import AgentEvent
from openclaw.agents.tool_loop import ToolLoopOrchestrator
from openclaw.events import Event

logger = logging.getLogger(__name__)


class AgentSession:
    """Pi-ai style agent session with automatic tool loop
    
    This class provides a clean API similar to pi-ai SDK:
    - session.prompt(text) - Send prompt and automatically handle tool loops
    - session.subscribe(handler) - Subscribe to events
    
    Example:
        ```python
        # Create session
        agent_session = AgentSession(
            session=session,
            runtime=runtime,
            tools=tools,
            system_prompt=system_prompt
        )
        
        # Subscribe to events
        def handle_event(event):
            print(f"Event: {event.type}")
        
        unsubscribe = agent_session.subscribe(handle_event)
        
        # Send prompt - automatically handles tool loop
        await agent_session.prompt("What's the weather today?")
        
        # Unsubscribe when done
        unsubscribe()
        ```
    """
    
    def __init__(
        self,
        session: Session,
        runtime: MultiProviderRuntime,
        tools: list[SimpleTool],
        system_prompt: str | None = None,
        max_iterations: int = 5,
        max_tokens: int = 4096,
        max_turns: int | None = None,
    ):
        """Initialize agent session
        
        Args:
            session: Underlying Session object for message persistence
            runtime: MultiProviderRuntime for LLM calls
            tools: Available tools for the agent
            system_prompt: Optional system prompt (stored in runtime)
            max_iterations: Maximum tool loop iterations
            max_tokens: Maximum tokens for LLM responses
            max_turns: Maximum conversation turns to keep in history
        """
        self.session = session
        self.runtime = runtime
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.max_turns = max_turns
        
        # Create orchestrator for tool loop handling
        self._orchestrator = ToolLoopOrchestrator(max_iterations=max_iterations)
        
        # Subscriber management (pi-ai style)
        self._subscribers: list[Callable[[Event | AgentEvent], Any]] = []
        
        # Track if session is active
        self._is_streaming = False
    
    @property
    def is_streaming(self) -> bool:
        """Check if session is currently streaming"""
        return self._is_streaming
    
    @property
    def session_id(self) -> str:
        """Get session ID"""
        return self.session.session_id
    
    @property
    def messages(self) -> list:
        """Get session messages"""
        return self.session.get_messages()
    
    def subscribe(self, handler: Callable[[Event | AgentEvent], Any]) -> Callable[[], None]:
        """Subscribe to session events (pi-ai style)
        
        Args:
            handler: Event handler function (sync or async)
            
        Returns:
            Unsubscribe function
        
        Example:
            ```python
            def on_text(event):
                if event.type == EventType.TEXT:
                    print(event.data.get('delta', {}).get('text', ''))
            
            unsubscribe = session.subscribe(on_text)
            # ... do work ...
            unsubscribe()  # Remove subscription
            ```
        """
        self._subscribers.append(handler)
        
        # Return unsubscribe function (pi-ai style)
        def unsubscribe():
            if handler in self._subscribers:
                self._subscribers.remove(handler)
        
        return unsubscribe
    
    async def prompt(
        self, 
        text: str,
        images: list[str] | None = None
    ) -> None:
        """Send prompt and automatically handle tool loop (pi-ai style)
        
        This is the main entry point for agent interaction. It:
        1. Adds user message to session
        2. Executes tool loop automatically
        3. Streams events to all subscribers
        4. Handles tool calls and follow-ups transparently
        
        Args:
            text: User prompt text
            images: Optional list of image URLs/paths
            
        Example:
            ```python
            await agent_session.prompt("What's 2+2?")
            # Agent automatically:
            # - Calls calculator tool if needed
            # - Gets result
            # - Provides final answer
            # All events streamed to subscribers
            ```
        """
        logger.info(f"🚀 AgentSession.prompt() called: {text[:100]}...")
        
        self._is_streaming = True
        
        try:
            # Execute tool loop with orchestrator
            async for event in self._orchestrator.execute_with_tools(
                session=self.session,
                prompt=text,
                tools=self.tools,
                runtime=self.runtime,
                images=images,
                max_tokens=self.max_tokens,
                max_turns=self.max_turns,
            ):
                # Notify all subscribers
                await self._notify_subscribers(event)
        
        finally:
            self._is_streaming = False
            logger.info("✅ AgentSession.prompt() complete")
    
    async def _notify_subscribers(self, event: Event | AgentEvent) -> None:
        """Notify all subscribers of an event
        
        Args:
            event: Event to broadcast
        """
        import asyncio
        
        for handler in self._subscribers:
            try:
                # Check if handler is async
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(
                    f"Error in event subscriber: {e}",
                    exc_info=True,
                    extra={"event_type": getattr(event, 'type', 'unknown')}
                )
    
    def reset(self) -> None:
        """Reset session (clear messages)
        
        This is useful for starting a new conversation while
        keeping the same session configuration.
        """
        logger.info(f"🔄 Resetting AgentSession {self.session_id}")
        self.session.clear_messages()
    
    def get_message_count(self) -> int:
        """Get number of messages in session"""
        return len(self.session.get_messages())
    
    def __repr__(self) -> str:
        return (
            f"AgentSession("
            f"id={self.session_id[:8]}..., "
            f"messages={self.get_message_count()}, "
            f"tools={len(self.tools)}, "
            f"streaming={self._is_streaming}"
            f")"
        )
