"""Main Agent class matching pi-mono's agent.ts

This module provides the high-level Agent API that wraps the agent loop
and provides a clean interface for agent interactions.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from .agent_loop import AgentLoop, AgentState
from .events import AgentEvent, AgentEventType, EventEmitter
from .providers import LLMProvider
from .tools.base import AgentTool

logger = logging.getLogger(__name__)


class _NullProvider(LLMProvider):
    """Null provider used when no real provider is given (for testing/structure validation)."""

    def __init__(self, model: str = "null/model", **kwargs):
        super().__init__(model=model, **kwargs)

    async def stream(self, messages, tools=None, max_tokens=4096, **kwargs):
        from .events import AgentEventType
        from .providers.base import LLMResponse
        yield LLMResponse(type="text_delta", content="(no provider configured)")
        yield LLMResponse(type="done", content="")

    def get_client(self):
        return None

    @property
    def provider_name(self) -> str:
        return "null"


class Agent:
    """
    Main Agent class providing high-level API for agent interactions
    
    This class matches pi-mono's Agent interface, providing:
    - State management (messages, model, tools, thinking level)
    - Steering/follow-up message queues
    - Event subscription API
    - Methods: prompt(), continue(), steer(), followUp(), abort()
    
    Example:
        ```python
        # Create agent
        agent = Agent(
            provider=provider,
            tools=tools,
            model="google/gemini-3-pro-preview"
        )
        
        # Subscribe to events
        agent.on(AgentEventType.TEXT_DELTA, lambda event: print(event.payload["delta"]))
        
        # Run agent
        messages = await agent.prompt("Hello, how are you?")
        ```
    """
    
    def __init__(
        self,
        provider: LLMProvider | None = None,
        tools: list[AgentTool] | None = None,
        model: str = "google/gemini-3-pro-preview",
        thinking_level: str = "off",
        system_prompt: str | None = None,
    ):
        """
        Initialize agent
        
        Args:
            provider: LLM provider for model inference (optional; a null provider is used if None)
            tools: List of available tools
            model: Model to use (format: "provider/model")
            thinking_level: Thinking level ("off", "on", "verbose")
            system_prompt: Optional system prompt
        """
        if provider is None:
            provider = _NullProvider(model=model)
        self.provider = provider
        self.tools = tools or []
        self.model = model
        self.thinking_level = thinking_level
        self.system_prompt = system_prompt
        
        # Event emitter for subscribing to events
        self.event_emitter = EventEmitter()
        
        # Create agent loop
        self.loop = AgentLoop(
            provider=provider,
            tools=self.tools,
            event_emitter=self.event_emitter
        )
        
        # Initialize state
        self.loop.state.model = model
        self.loop.state.tools = self.tools
        self.loop.state.thinking_level = thinking_level
    
    async def prompt(
        self,
        message: str | list[Any],
        system_prompt: str | None = None,
        images: list[str] | None = None,
    ):
        """
        Send prompt and yield agent events as they are emitted.

        This is an async generator — callers use ``async for event in agent.prompt(...)``.

        Args:
            message: User message string, list of strings, or list of UserMessage objects.
            system_prompt: Optional system prompt override.
            images: Optional list of image URLs or file paths.

        Yields:
            AgentEvent objects (AgentStartEvent, TextDeltaEvent, AgentEndEvent, …).
        """
        import asyncio as _asyncio
        from .agent_loop import AgentMessage
        from .events import AgentEvent

        # Collect events through a queue so the generator can yield them while
        # the agent loop runs concurrently.
        queue: _asyncio.Queue[AgentEvent | None] = _asyncio.Queue()

        def _on_event(event: AgentEvent) -> None:
            queue.put_nowait(event)

        # Subscribe to all event types via a wildcard listener
        self.event_emitter.on("*", _on_event)

        # Build prompts list
        if isinstance(message, str):
            prompts = [message]
        elif message and hasattr(message[0], "content"):
            # UserMessage objects — extract content strings
            prompts = [m.content if hasattr(m, "content") else str(m) for m in message]
        else:
            prompts = list(message)

        sys_prompt = system_prompt or self.system_prompt

        # Run the agent loop as a background task
        async def _run() -> None:
            try:
                if images and prompts:
                    self.loop.state.messages = []
                    if sys_prompt:
                        self.loop.state.messages.append(AgentMessage(
                            role="system", content=sys_prompt
                        ))
                    self.loop.state.messages.append(AgentMessage(
                        role="user", content=prompts[0], images=images
                    ))
                    for p in prompts[1:]:
                        self.loop.state.messages.append(AgentMessage(role="user", content=p))
                    await self.loop.agent_loop_continue()
                else:
                    await self.loop.agent_loop(
                        prompts=prompts,
                        system_prompt=sys_prompt,
                        model=self.model,
                    )
            finally:
                queue.put_nowait(None)  # sentinel

        task = _asyncio.create_task(_run())

        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self.event_emitter.off("*", _on_event)
            if not task.done():
                task.cancel()
                try:
                    await task
                except (_asyncio.CancelledError, Exception):
                    pass
    
    async def continue_conversation(self) -> list[Any]:
        """
        Continue conversation from current state
        
        Returns:
            List of messages in conversation
        """
        messages = await self.loop.agent_loop_continue()
        return messages
    
    def steer(self, message: str) -> None:
        """
        Add steering message (interrupts current execution)
        
        Steering messages are processed immediately, interrupting
        any ongoing tool execution or agent turns.
        
        Args:
            message: Steering message to inject
        """
        self.loop.steer(message)
    
    def follow_up(self, message: str) -> None:
        """
        Add follow-up message (queued after current turn)
        
        Follow-up messages are queued and processed after the
        current turn completes.
        
        Args:
            message: Follow-up message to queue
        """
        self.loop.followup(message)
    
    def abort(self) -> None:
        """
        Abort agent execution
        
        Stops the agent loop at the next checkpoint.
        """
        self.loop.abort()
    
    def on(self, event_type: AgentEventType | str, callback: Callable[[AgentEvent], None]) -> None:
        """
        Subscribe to agent events
        
        Args:
            event_type: Type of event to listen for
            callback: Callback function to call when event occurs
            
        Example:
            ```python
            def handle_text(event: AgentEvent):
                print(event.payload["delta"])
            
            agent.on(AgentEventType.TEXT_DELTA, handle_text)
            ```
        """
        self.event_emitter.on(event_type, callback)
    
    def off(self, event_type: AgentEventType | str, callback: Callable[[AgentEvent], None]) -> None:
        """
        Unsubscribe from agent events
        
        Args:
            event_type: Type of event to stop listening for
            callback: Callback function to remove
        """
        self.event_emitter.off(event_type, callback)
    
    def once(self, event_type: AgentEventType | str, callback: Callable[[AgentEvent], None]) -> None:
        """
        Subscribe to agent event once
        
        The callback will be called once and then automatically unsubscribed.
        
        Args:
            event_type: Type of event to listen for
            callback: Callback function to call once
        """
        self.event_emitter.once(event_type, callback)
    
    @property
    def state(self) -> AgentState:
        """
        Get current agent state
        
        Returns:
            Current agent state including messages, model, tools
        """
        return self.loop.state
    
    @property
    def messages(self) -> list[Any]:
        """
        Get conversation messages
        
        Returns:
            List of messages in current conversation
        """
        return self.loop.state.messages
    
    def get_message_history(self) -> list[dict[str, Any]]:
        """
        Get conversation history in serializable format
        
        Returns:
            List of message dictionaries
        """
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": getattr(msg, "tool_calls", None),
                "tool_call_id": getattr(msg, "tool_call_id", None),
            }
            for msg in self.messages
        ]
    
    def set_model(self, model: str) -> None:
        """
        Change the model used by agent
        
        Args:
            model: New model to use (format: "provider/model")
        """
        self.model = model
        self.loop.state.model = model
    
    def set_thinking_level(self, level: str) -> None:
        """
        Change thinking level
        
        Args:
            level: Thinking level ("off", "on", "verbose")
        """
        self.thinking_level = level
        self.loop.state.thinking_level = level
    
    def add_tool(self, tool: AgentTool) -> None:
        """
        Add tool to agent
        
        Args:
            tool: Tool to add
        """
        if tool not in self.tools:
            self.tools.append(tool)
            self.loop.tools[tool.name] = tool
            self.loop.state.tools = self.tools
    
    def remove_tool(self, tool_name: str) -> None:
        """
        Remove tool from agent
        
        Args:
            tool_name: Name of tool to remove
        """
        self.tools = [t for t in self.tools if t.name != tool_name]
        if tool_name in self.loop.tools:
            del self.loop.tools[tool_name]
        self.loop.state.tools = self.tools
    
    def clear_messages(self) -> None:
        """Clear conversation history"""
        self.loop.state.messages = []
        self.loop.state.turn_number = 0
    
    async def wait_for_idle(self) -> None:
        """
        Wait until agent completes all operations
        
        Useful for synchronizing with agent execution in tests or scripts.
        Matches TypeScript Agent.waitForIdle()
        """
        # Wait while agent is streaming or has pending tool calls
        while self.loop.state.is_streaming or self.loop.state.pending_tool_calls:
            await asyncio.sleep(0.1)
        
        # Also wait for queues to be empty
        while self.loop.state.steering_queue or self.loop.state.followup_queue:
            await asyncio.sleep(0.1)
    
    async def compact(self) -> None:
        """
        Manually trigger context compaction
        
        Summarizes conversation history to reduce context window usage.
        Matches TypeScript Agent.compact()
        """
        from .compaction.compactor import compact_messages
        
        try:
            logger.info("Starting manual compaction")
            
            # Compact messages using compactor
            compacted = await compact_messages(
                messages=self.loop.state.messages,
                provider=self.provider,
                model=self.model
            )
            
            # Replace messages with compacted version
            self.loop.state.messages = compacted
            
            logger.info(f"Compaction complete: {len(compacted)} messages")
        
        except Exception as e:
            logger.error(f"Compaction failed: {e}", exc_info=True)
            # Don't fail the agent, just log error
    
    def __repr__(self) -> str:
        return f"Agent(model={self.model}, tools={len(self.tools)}, messages={len(self.messages)})"
