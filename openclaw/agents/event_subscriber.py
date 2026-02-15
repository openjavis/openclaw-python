"""
Event Subscriber - handles agent event stream processing

Aligned with openclaw/src/agents/pi-embedded-subscribe.ts

This module implements the event subscription and processing logic that handles
agent events (messages, tool executions, etc.) and manages state tracking.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, Optional

logger = logging.getLogger(__name__)


@dataclass
class EventSubscriberState:
    """
    Event subscriber state tracking
    
    Matches TypeScript SubscribeState from pi-embedded-subscribe.ts
    """
    assistant_texts: list[str] = field(default_factory=list)
    """Accumulated assistant text blocks"""
    
    tool_metas: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Tool execution metadata by tool_id"""
    
    messaging_tool_sent: dict[str, bool] = field(default_factory=dict)
    """Track which messaging tools have sent (for deduplication)"""
    
    last_tool_error: str | None = None
    """Last tool execution error"""
    
    delta_buffer: str = ""
    """Current text delta buffer"""
    
    block_reply_buffer: list[str] = field(default_factory=list)
    """Pending block replies"""
    
    current_message_id: str | None = None
    """Current assistant message ID"""


class EventSubscriber:
    """
    Agent event subscriber and processor
    
    Handles event stream from agent runtime and manages state.
    Matches TypeScript subscribeEmbeddedPiSession functionality.
    """
    
    def __init__(
        self,
        callbacks: dict[str, Callable[..., Awaitable[Any]]] | None = None,
        block_reply_mode: str = "text_end",
    ):
        """
        Initialize event subscriber
        
        Args:
            callbacks: Event callbacks (on_block_reply, on_tool_start, etc.)
            block_reply_mode: "text_end" or "message_end"
        """
        self.state = EventSubscriberState()
        self.callbacks = callbacks or {}
        self.block_reply_mode = block_reply_mode
    
    async def handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Route event to appropriate handler
        
        Args:
            event_type: Event type string
            data: Event data
        """
        if event_type == "message_start":
            await self.handle_message_start(data)
        elif event_type == "message_update":
            await self.handle_message_update(data)
        elif event_type == "message_end":
            await self.handle_message_end(data)
        elif event_type == "tool_execution_start":
            await self.handle_tool_execution_start(data)
        elif event_type == "tool_execution_update":
            await self.handle_tool_execution_update(data)
        elif event_type == "tool_execution_end":
            await self.handle_tool_execution_end(data)
        else:
            logger.debug(f"Unhandled event type: {event_type}")
    
    async def handle_message_start(self, data: dict[str, Any]) -> None:
        """
        Handle assistant message start
        
        Matches handleMessageStart from pi-embedded-subscribe.handlers.messages.ts
        """
        self.state.current_message_id = data.get("id")
        self.state.delta_buffer = ""
        
        if self.callbacks.get("on_assistant_message_start"):
            await self.callbacks["on_assistant_message_start"](data)
    
    async def handle_message_update(self, data: dict[str, Any]) -> None:
        """
        Handle message update (text_delta, text_start, text_end)
        
        Matches handleMessageUpdate from pi-embedded-subscribe.handlers.messages.ts
        """
        # Handle text_delta
        if "text_delta" in data:
            delta = data["text_delta"]
            self.state.delta_buffer += delta
            
            # Block reply handling (if enabled)
            if self.block_reply_mode == "text_end" and self.callbacks.get("on_block_reply"):
                await self.callbacks["on_block_reply"](delta)
        
        # Handle text_start
        if "text_start" in data:
            # Reset delta buffer at text start
            self.state.delta_buffer = ""
        
        # Handle text_end
        if "text_end" in data:
            # Flush buffer to assistant texts
            if self.state.delta_buffer:
                self.state.assistant_texts.append(self.state.delta_buffer)
            
            # Trigger block reply flush if in text_end mode
            if self.block_reply_mode == "text_end" and self.callbacks.get("flush_block_replies"):
                await self.callbacks["flush_block_replies"]()
            
            self.state.delta_buffer = ""
    
    async def handle_message_end(self, data: dict[str, Any]) -> None:
        """
        Handle assistant message end
        
        Matches handleMessageEnd from pi-embedded-subscribe.handlers.messages.ts
        """
        # Flush any remaining buffer
        if self.state.delta_buffer:
            self.state.assistant_texts.append(self.state.delta_buffer)
            self.state.delta_buffer = ""
        
        # Flush block replies if in message_end mode
        if self.block_reply_mode == "message_end" and self.callbacks.get("flush_block_replies"):
            await self.callbacks["flush_block_replies"]()
        
        if self.callbacks.get("on_assistant_message_end"):
            await self.callbacks["on_assistant_message_end"](data)
    
    async def handle_tool_execution_start(self, data: dict[str, Any]) -> None:
        """
        Handle tool execution start
        
        Matches handleToolExecutionStart from pi-embedded-subscribe.handlers.tools.ts
        """
        tool_name = data.get("name")
        tool_id = data.get("id")
        
        # Flush pending block replies before tool execution
        if self.callbacks.get("flush_block_replies"):
            await self.callbacks["flush_block_replies"]()
        
        # Record tool metadata
        self.state.tool_metas[tool_id] = {
            "name": tool_name,
            "started_at": data.get("timestamp"),
            "args": data.get("args"),
        }
        
        # Emit tool start event
        if self.callbacks.get("on_tool_start"):
            await self.callbacks["on_tool_start"](tool_name, tool_id, data)
    
    async def handle_tool_execution_update(self, data: dict[str, Any]) -> None:
        """
        Handle tool execution update (partial results)
        
        Matches handleToolExecutionUpdate from pi-embedded-subscribe.handlers.tools.ts
        """
        tool_id = data.get("id")
        
        if self.callbacks.get("on_tool_update"):
            await self.callbacks["on_tool_update"](tool_id, data)
    
    async def handle_tool_execution_end(self, data: dict[str, Any]) -> None:
        """
        Handle tool execution end
        
        Matches handleToolExecutionEnd from pi-embedded-subscribe.handlers.tools.ts
        """
        tool_name = data.get("name")
        tool_id = data.get("id")
        success = data.get("success", False)
        
        # Extract result or error
        if success:
            result = data.get("result")
            self.state.last_tool_error = None
        else:
            error = data.get("error", "Unknown error")
            self.state.last_tool_error = error
            result = None
        
        # For messaging tools, track sent status and commit text
        if tool_name in ["telegram", "discord", "slack", "signal"] and success:
            sent_text = None
            if isinstance(result, dict):
                sent_text = result.get("text") or result.get("content")
            elif isinstance(result, str):
                sent_text = result
            
            if sent_text:
                self.state.messaging_tool_sent[tool_id] = True
                self.state.assistant_texts.append(sent_text)
                logger.info(f"Messaging tool {tool_name} sent text, marking as committed")
        
        # Emit tool end event
        if self.callbacks.get("on_tool_end"):
            await self.callbacks["on_tool_end"](tool_name, tool_id, success, result)
    
    async def flush_block_replies(self) -> None:
        """Flush any pending block replies"""
        if self.state.delta_buffer and self.callbacks.get("send_block_reply"):
            await self.callbacks["send_block_reply"](self.state.delta_buffer)
            self.state.delta_buffer = ""
    
    def get_assistant_text(self) -> str:
        """Get accumulated assistant text"""
        return "".join(self.state.assistant_texts)
    
    def has_messaging_tool_sent(self) -> bool:
        """Check if any messaging tool has sent"""
        return any(self.state.messaging_tool_sent.values())
    
    def reset(self) -> None:
        """Reset subscriber state"""
        self.state = EventSubscriberState()


def detect_block_reply_end(text: str, mode: str = "text_end") -> bool:
    """
    Detect if block reply should be flushed
    
    Args:
        text: Current text
        mode: "text_end" or "message_end"
        
    Returns:
        True if should flush block reply
    """
    if mode == "text_end":
        # Flush on every text_end event
        return True
    elif mode == "message_end":
        # Only flush at message_end
        return False
    return False


def strip_block_tags(text: str) -> str:
    """
    Strip block reply tags from text
    
    Removes <block_reply> tags that mark intermediate responses
    """
    # Remove <block_reply> and </block_reply> tags
    text = text.replace("<block_reply>", "")
    text = text.replace("</block_reply>", "")
    return text
