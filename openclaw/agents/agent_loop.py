"""Agent loop implementation matching pi-mono's agent-loop.ts

This module implements the core agent execution loop with:
- Streaming LLM responses
- Tool call extraction and execution
- Steering support (interrupting messages)
- Event emission for all steps
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from .events import (
    AgentEndEvent,
    AgentEvent,
    AgentStartEvent,
    EventEmitter,
    MessageEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    TextDeltaEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ThinkingStartEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolExecutionEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    TurnEndEvent,
    TurnStartEvent,
)
from .providers import LLMMessage, LLMProvider
from .tools.base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class AgentState:
    """Agent execution state"""
    
    def __init__(self):
        self.messages: list[LLMMessage] = []
        self.model: str = "google/gemini-3-pro-preview"
        self.tools: list[AgentTool] = []
        self.thinking_level: str = "off"
        self.steering_queue: list[str] = []
        self.followup_queue: list[str] = []
        self.aborted: bool = False
        self.turn_number: int = 0


class AgentLoop:
    """Core agent execution loop"""
    
    def __init__(
        self,
        provider: LLMProvider,
        tools: list[AgentTool],
        event_emitter: EventEmitter | None = None,
    ):
        self.provider = provider
        self.tools = {tool.name: tool for tool in tools}
        self.event_emitter = event_emitter or EventEmitter()
        self.state = AgentState()
    
    async def agent_loop(
        self,
        prompts: list[str],
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> list[LLMMessage]:
        """
        Start agent loop with new prompts
        
        Args:
            prompts: User messages to process
            system_prompt: Optional system prompt
            model: Optional model override
            
        Returns:
            Final message list
        """
        # Initialize state
        self.state.messages = []
        self.state.turn_number = 0
        
        if model:
            self.state.model = model
        
        # Add system prompt if provided
        if system_prompt:
            self.state.messages.append(LLMMessage(
                role="system",
                content=system_prompt
            ))
        
        # Add user prompts
        for prompt in prompts:
            self.state.messages.append(LLMMessage(
                role="user",
                content=prompt
            ))
        
        # Emit agent start
        await self.event_emitter.emit(AgentStartEvent(model=self.state.model))
        
        try:
            # Run main loop
            await self.run_loop()
            
            # Emit agent end
            await self.event_emitter.emit(AgentEndEvent(reason="completed"))
            
            return self.state.messages
            
        except Exception as e:
            logger.error(f"Agent loop error: {e}", exc_info=True)
            await self.event_emitter.emit(AgentEndEvent(reason="error"))
            raise
    
    async def agent_loop_continue(self) -> list[LLMMessage]:
        """
        Continue agent loop from existing state
        
        Returns:
            Final message list
        """
        try:
            await self.run_loop()
            return self.state.messages
        except Exception as e:
            logger.error(f"Agent loop continue error: {e}", exc_info=True)
            raise
    
    async def run_loop(self) -> None:
        """Main execution loop"""
        
        while True:
            # Check for abort
            if self.state.aborted:
                logger.info("Agent loop aborted")
                break
            
            # Check for steering messages (interrupts)
            if self.state.steering_queue:
                steering_msg = self.state.steering_queue.pop(0)
                self.state.messages.append(LLMMessage(
                    role="user",
                    content=steering_msg
                ))
                logger.info("Processing steering message")
                continue
            
            # Increment turn
            self.state.turn_number += 1
            
            # Emit turn start
            await self.event_emitter.emit(TurnStartEvent(
                turn_number=self.state.turn_number
            ))
            
            # Stream assistant response
            assistant_message, tool_calls = await self.stream_assistant_response()
            
            # Add assistant message to context
            self.state.messages.append(assistant_message)
            
            # Emit turn end
            await self.event_emitter.emit(TurnEndEvent(
                turn_number=self.state.turn_number,
                has_tool_calls=len(tool_calls) > 0
            ))
            
            # If no tool calls, we're done
            if not tool_calls:
                break
            
            # Execute tool calls
            await self.execute_tool_calls(tool_calls)
            
            # Check for follow-up messages
            if self.state.followup_queue:
                followup_msg = self.state.followup_queue.pop(0)
                self.state.messages.append(LLMMessage(
                    role="user",
                    content=followup_msg
                ))
    
    async def stream_assistant_response(self) -> tuple[LLMMessage, list[dict[str, Any]]]:
        """
        Stream assistant response from LLM
        
        Returns:
            Tuple of (assistant_message, tool_calls)
        """
        # Emit message start
        message_id = str(uuid.uuid4())
        await self.event_emitter.emit(MessageStartEvent(
            role="assistant",
            message_id=message_id
        ))
        
        # Accumulate response
        content_parts: list[str] = []
        thinking_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        current_tool_call: dict[str, Any] | None = None
        in_thinking = False
        
        try:
            # Stream from provider
            async for response in self.provider.stream(
                messages=self.state.messages,
                model=self.state.model,
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.get_schema()
                        }
                    }
                    for tool in self.tools.values()
                ]
            ):
                # Handle LLMResponse objects from providers
                event_type = response.type
                
                if event_type == "thinking_start":
                    in_thinking = True
                    await self.event_emitter.emit(ThinkingStartEvent())
                
                elif event_type == "thinking_delta":
                    delta = str(response.content)
                    thinking_parts.append(delta)
                    await self.event_emitter.emit(ThinkingDeltaEvent(delta=delta))
                
                elif event_type == "thinking_end":
                    in_thinking = False
                    await self.event_emitter.emit(ThinkingEndEvent(
                        thinking="".join(thinking_parts)
                    ))
                
                elif event_type == "text_delta":
                    delta = str(response.content)
                    content_parts.append(delta)
                    await self.event_emitter.emit(TextDeltaEvent(delta=delta))
                    
                    # Also emit message update
                    await self.event_emitter.emit(MessageUpdateEvent(
                        role="assistant",
                        content="".join(content_parts)
                    ))
                
                elif event_type == "tool_call":
                    # Handle tool calls from response
                    if response.tool_calls:
                        for tc in response.tool_calls:
                            tool_call_id = tc.get("id") or str(uuid.uuid4())
                            tool_name = tc.get("name", "")
                            params = tc.get("arguments", {})
                            
                            # Emit tool call events
                            await self.event_emitter.emit(ToolCallStartEvent(
                                tool_call_id=tool_call_id,
                                tool_name=tool_name
                            ))
                            
                            await self.event_emitter.emit(ToolCallEndEvent(
                                tool_call_id=tool_call_id,
                                tool_name=tool_name,
                                params=params
                            ))
                            
                            tool_calls.append({
                                "id": tool_call_id,
                                "name": tool_name,
                                "params": params
                            })
                
                elif event_type == "done":
                    break
        
        except Exception as e:
            logger.error(f"Error streaming response: {e}", exc_info=True)
            raise
        
        # Build final message
        content = "".join(content_parts)
        
        assistant_message = LLMMessage(
            role="assistant",
            content=content
        )
        
        # Add tool calls if any
        if tool_calls:
            assistant_message.tool_calls = tool_calls
        
        # Emit message end
        await self.event_emitter.emit(MessageEndEvent(
            role="assistant",
            content=content,
            message_id=message_id
        ))
        
        return assistant_message, tool_calls
    
    async def execute_tool_calls(self, tool_calls: list[dict[str, Any]]) -> None:
        """
        Execute tool calls sequentially, checking for steering after each
        
        Args:
            tool_calls: List of tool calls to execute
        """
        for tool_call in tool_calls:
            # Check for steering before each tool
            if self.state.steering_queue:
                logger.info("Steering detected, stopping tool execution")
                break
            
            tool_call_id = tool_call["id"]
            tool_name = tool_call["name"]
            params = tool_call.get("params", {})
            
            # Emit tool execution start
            await self.event_emitter.emit(ToolExecutionStartEvent(
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                params=params
            ))
            
            try:
                # Get tool
                tool = self.tools.get(tool_name)
                if not tool:
                    error_msg = f"Tool '{tool_name}' not found"
                    logger.error(error_msg)
                    
                    # Emit error
                    await self.event_emitter.emit(ToolExecutionEndEvent(
                        tool_call_id=tool_call_id,
                        success=False,
                        error=error_msg
                    ))
                    
                    # Add error result to messages
                    self.state.messages.append(LLMMessage(
                        role="toolResult",
                        tool_call_id=tool_call_id,
                        content=f"Error: {error_msg}"
                    ))
                    continue
                
                # Execute tool
                result: ToolResult = await tool.execute(params)
                
                # Emit tool execution end
                await self.event_emitter.emit(ToolExecutionEndEvent(
                    tool_call_id=tool_call_id,
                    success=result.success,
                    result=result.content if result.success else None,
                    error=result.error if not result.success else None
                ))
                
                # Add result to messages
                result_content = result.content if result.success else f"Error: {result.error}"
                self.state.messages.append(LLMMessage(
                    role="toolResult",
                    tool_call_id=tool_call_id,
                    content=result_content
                ))
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Tool execution error: {e}", exc_info=True)
                
                # Emit error
                await self.event_emitter.emit(ToolExecutionEndEvent(
                    tool_call_id=tool_call_id,
                    success=False,
                    error=error_msg
                ))
                
                # Add error result
                self.state.messages.append(LLMMessage(
                    role="toolResult",
                    tool_call_id=tool_call_id,
                    content=f"Error: {error_msg}"
                ))
    
    def steer(self, message: str) -> None:
        """
        Add steering message (interrupts current execution)
        
        Args:
            message: Steering message to add
        """
        self.state.steering_queue.append(message)
    
    def followup(self, message: str) -> None:
        """
        Add follow-up message (queued after current turn)
        
        Args:
            message: Follow-up message to add
        """
        self.state.followup_queue.append(message)
    
    def abort(self) -> None:
        """Abort agent loop"""
        self.state.aborted = True
