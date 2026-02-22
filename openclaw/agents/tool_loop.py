"""Tool loop orchestrator - pi-ai style automatic tool execution

This module provides automatic tool loop handling similar to pi-ai SDK,
extracting the manual loop logic from MultiProviderRuntime.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openclaw.agents.runtime import MultiProviderRuntime
    from openclaw.agents.session import Session
    from openclaw.agents.tools.base import SimpleTool

from openclaw.agents.events import AgentEvent
from openclaw.agents.history_utils import limit_history_turns, sanitize_session_history
from openclaw.agents.providers.base import LLMMessage
from openclaw.events import Event, EventType

logger = logging.getLogger(__name__)

# Maximum tool call iterations to prevent infinite loops
MAX_TOOL_ITERATIONS = 5


@dataclass
class ToolResult:
    """Result from a single tool execution"""
    
    tool_call_id: str
    tool_name: str
    success: bool
    result: str
    error: str | None = None


@dataclass
class TurnResult:
    """Result from a complete turn (initial + follow-ups)"""
    
    text: str
    tool_results: list[ToolResult]
    iterations: int
    stopped_by_max_iterations: bool = False
    stopped_by_loop_detection: bool = False


class ToolLoopOrchestrator:
    """Orchestrates automatic tool loop execution pi-ai style
    
    This class handles:
    - Initial LLM call with tools
    - Tool execution
    - Follow-up calls after tool results
    - Loop detection and iteration limits
    - Event streaming to subscribers
    """
    
    def __init__(self, max_iterations: int = MAX_TOOL_ITERATIONS):
        self.max_iterations = max_iterations
        self._observers: list[Any] = []
    
    def add_observer(self, observer: Any) -> None:
        """Add an event observer"""
        self._observers.append(observer)
    
    def remove_observer(self, observer: Any) -> None:
        """Remove an event observer"""
        if observer in self._observers:
            self._observers.remove(observer)
    
    async def _notify_observers(self, event: Event | AgentEvent) -> None:
        """Notify all observers of an event"""
        for observer in self._observers:
            try:
                if asyncio.iscoroutinefunction(observer):
                    await observer(event)
                else:
                    observer(event)
            except Exception as e:
                logger.error(f"Error notifying observer: {e}", exc_info=True)
    
    async def execute_with_tools(
        self,
        session: Session,
        prompt: str,
        tools: list[SimpleTool],
        runtime: MultiProviderRuntime,
        images: list[str] | None = None,
        max_tokens: int = 4096,
        max_turns: int | None = None,
        hook_before_tool_call: Any = None,
        hook_after_tool_call: Any = None,
        hook_llm_input: Any = None,
        hook_llm_output: Any = None,
    ) -> AsyncIterator[Event | AgentEvent]:
        """Execute a turn with automatic tool loop handling
        
        This mimics pi-ai's session.prompt() behavior:
        1. Make initial LLM call with tools
        2. If tools are called:
           - Execute tools
           - Make follow-up call with results
           - Repeat until no more tool calls or max iterations reached
        3. Stream all events to subscribers
        
        Args:
            session: Session to execute in
            prompt: User prompt
            tools: Available tools
            runtime: Runtime to use for LLM calls
            images: Optional images
            max_tokens: Max tokens for LLM
            max_turns: Max conversation turns to keep in history
            
        Yields:
            Events from the execution
        """
        logger.info(f"🔄 Starting tool loop orchestration (max_iterations={self.max_iterations})")
        
        iteration = 0
        needs_followup = False
        accumulated_text = ""
        all_tool_results: list[ToolResult] = []
        
        # Add user message to session
        if images:
            # If images provided, add them to the message content or metadata
            session.add_user_message(prompt)
            # Note: Image handling would need to be added to Session class
            # For now, we pass images through _stream_single_turn
        else:
            session.add_user_message(prompt)
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"🔄 Tool loop iteration {iteration}/{self.max_iterations}")
            
            # Prepare messages for this iteration
            if iteration == 1:
                # Initial call - use session messages
                messages = self._prepare_messages(session, max_turns, runtime.provider_name)
            else:
                # Follow-up call - session already has tool results added
                messages = self._prepare_messages(session, max_turns, runtime.provider_name)
            
            # --- llm_input hook ---
            if hook_llm_input:
                try:
                    await hook_llm_input({"messages": messages, "tools": tools, "iteration": iteration})
                except Exception as _he:
                    logger.debug(f"llm_input hook error: {_he}")

            # Make LLM call
            turn_text = ""
            turn_tool_calls = []
            raw_llm_output: dict = {}

            # Stream from runtime's single-turn execution
            async for event in runtime._stream_single_turn(
                session=session,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                is_followup=(iteration > 1)
            ):
                # Forward event to subscribers
                await self._notify_observers(event)
                yield event

                # Track what happened
                if hasattr(event, 'type'):
                    if event.type in (EventType.AGENT_TEXT, EventType.TEXT, "text_delta"):
                        # Accumulate text
                        if hasattr(event, 'data') and isinstance(event.data, dict):
                            delta_data = event.data.get('delta', {})
                            if isinstance(delta_data, dict):
                                delta_text = delta_data.get('text', '')
                            else:
                                delta_text = str(delta_data)
                            turn_text += delta_text
                            raw_llm_output.setdefault("text", "")
                            raw_llm_output["text"] += delta_text

                    elif event.type == EventType.TOOL_EXECUTION_END:
                        # --- after_tool_call hook ---
                        if hasattr(event, 'data') and isinstance(event.data, dict):
                            tool_result = ToolResult(
                                tool_call_id=event.data.get('tool_call_id', ''),
                                tool_name=event.data.get('tool_name', ''),
                                success=event.data.get('success', False),
                                result=str(event.data.get('result', '')),
                                error=event.data.get('error')
                            )
                            all_tool_results.append(tool_result)
                            turn_tool_calls.append(tool_result)
                            if hook_after_tool_call:
                                try:
                                    await hook_after_tool_call({
                                        "tool_name": tool_result.tool_name,
                                        "tool_call_id": tool_result.tool_call_id,
                                        "success": tool_result.success,
                                        "result": tool_result.result,
                                    })
                                except Exception as _he:
                                    logger.debug(f"after_tool_call hook error: {_he}")

                    elif event.type == EventType.TOOL_EXECUTION_START:
                        # --- before_tool_call hook ---
                        if hook_before_tool_call and hasattr(event, 'data') and isinstance(event.data, dict):
                            try:
                                await hook_before_tool_call({
                                    "tool_name": event.data.get('tool_name', ''),
                                    "tool_call_id": event.data.get('tool_call_id', ''),
                                    "arguments": event.data.get('arguments', {}),
                                })
                            except Exception as _he:
                                logger.debug(f"before_tool_call hook error: {_he}")

            # --- llm_output hook ---
            if hook_llm_output and raw_llm_output:
                try:
                    await hook_llm_output({"output": raw_llm_output, "iteration": iteration})
                except Exception as _he:
                    logger.debug(f"llm_output hook error: {_he}")
            
            # Check if we need follow-up
            if turn_tool_calls:
                logger.info(f"🔧 {len(turn_tool_calls)} tools executed, checking for follow-up...")
                
                # Check if this was already a follow-up with tool calls (loop detection)
                if iteration > 1:
                    logger.warning(f"🔴 Tool call loop detected in iteration {iteration}")
                    logger.warning(f"🛑 Stopping to prevent infinite loop")
                    
                    # Provide fallback response
                    if not turn_text:
                        fallback_text = "I've executed the requested tools. The results are ready."
                        session.add_assistant_message(content=fallback_text)
                        
                        # Send fallback text event
                        fallback_event = Event(
                            type=EventType.TEXT,
                            source="tool-loop-orchestrator",
                            session_id=session.session_id,
                            data={"delta": {"text": fallback_text}},
                        )
                        await self._notify_observers(fallback_event)
                        yield fallback_event
                    
                    # Send turn complete
                    complete_event = Event(
                        type=EventType.AGENT_TURN_COMPLETE,
                        source="tool-loop-orchestrator",
                        session_id=session.session_id,
                        data={
                            "iterations": iteration,
                            "stopped_by_loop_detection": True
                        },
                    )
                    await self._notify_observers(complete_event)
                    yield complete_event
                    return
                
                # Continue to next iteration (follow-up)
                needs_followup = True
                accumulated_text += turn_text
                continue
            else:
                # No tool calls - we're done
                accumulated_text += turn_text
                logger.info(f"✅ Tool loop complete after {iteration} iteration(s)")
                break
        
        # Check if we stopped due to max iterations
        if iteration >= self.max_iterations and needs_followup:
            logger.error(f"🔴 Maximum tool iterations ({self.max_iterations}) reached")
            
            # Provide fallback response if no text accumulated
            if not accumulated_text:
                fallback_text = "I've executed multiple tools but encountered difficulty generating a final response. The tool results have been processed."
                session.add_assistant_message(content=fallback_text)
                
                # Send fallback text event
                fallback_event = Event(
                    type=EventType.TEXT,
                    source="tool-loop-orchestrator",
                    session_id=session.session_id,
                    data={"delta": {"text": fallback_text}},
                )
                await self._notify_observers(fallback_event)
                yield fallback_event
            
            # Send turn complete
            complete_event = Event(
                type=EventType.AGENT_TURN_COMPLETE,
                source="tool-loop-orchestrator",
                session_id=session.session_id,
                data={
                    "iterations": iteration,
                    "stopped_by_max_iterations": True
                },
            )
            await self._notify_observers(complete_event)
            yield complete_event
            return
        
        # Send final turn complete event
        complete_event = Event(
            type=EventType.AGENT_TURN_COMPLETE,
            source="tool-loop-orchestrator",
            session_id=session.session_id,
            data={
                "iterations": iteration,
                "stopped_by_max_iterations": False,
                "stopped_by_loop_detection": False
            },
        )
        await self._notify_observers(complete_event)
        yield complete_event
    
    def _prepare_messages(
        self,
        session: Session,
        max_turns: int | None,
        provider_name: str
    ) -> list[LLMMessage]:
        """Prepare messages for LLM call with history limiting
        
        Args:
            session: Session with messages
            max_turns: Max conversation turns to keep
            provider_name: Provider name for history limiting
            
        Returns:
            List of LLMMessage ready for provider
        """
        # Get all messages
        all_messages = session.get_messages()
        
        # Convert to dict format
        messages_dict = [
            {
                "role": m.role,
                "content": m.content,
                "tool_calls": getattr(m, 'tool_calls', None),
                "tool_call_id": getattr(m, 'tool_call_id', None),
                "name": getattr(m, 'name', None),
            }
            for m in all_messages
        ]
        
        # Sanitize history
        sanitized = sanitize_session_history(messages_dict)
        
        # Limit history
        limited = limit_history_turns(
            sanitized,
            max_turns=max_turns,
            provider=provider_name
        )
        
        logger.info(f"📝 Prepared messages: {len(all_messages)} -> {len(limited)} (after sanitization and limiting)")
        
        # Convert to LLMMessage
        llm_messages = []
        for m in limited:
            llm_messages.append(LLMMessage(
                role=m["role"],
                content=m["content"],
                images=None,  # Images handled separately
                tool_calls=m.get("tool_calls"),
                tool_call_id=m.get("tool_call_id"),
                name=m.get("name")
            ))
        
        return llm_messages
