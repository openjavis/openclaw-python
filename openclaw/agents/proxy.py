"""Stream proxy function matching pi-mono's proxy.ts

This module provides server-side stream routing and bandwidth optimization
by stripping the `partial` field to reduce payload size.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from .events import AgentEvent

logger = logging.getLogger(__name__)


async def stream_proxy(
    event_stream: AsyncIterator[AgentEvent],
    strip_partial: bool = True,
) -> AsyncIterator[dict[str, Any]]:
    """
    Proxy stream function for server-side routing
    
    This function:
    1. Strips the `partial` field from events to reduce bandwidth
    2. Converts events to serializable dictionaries
    3. Handles error recovery
    
    Args:
        event_stream: AsyncIterator of AgentEvent objects
        strip_partial: Whether to strip partial field (default: True)
        
    Yields:
        Event dictionaries ready for transmission
        
    Example:
        ```python
        async for event in stream_proxy(agent_events):
            await websocket.send_json(event)
        ```
    """
    try:
        async for event in event_stream:
            # Convert event to dict
            event_dict = {
                "type": event.type.value if hasattr(event.type, "value") else str(event.type),
                "timestamp": event.timestamp,
                "payload": event.payload.copy()
            }
            
            # Strip partial field if requested (bandwidth optimization)
            if strip_partial and "partial" in event_dict["payload"]:
                del event_dict["payload"]["partial"]
            
            yield event_dict
            
    except asyncio.CancelledError:
        logger.info("Stream proxy cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in stream proxy: {e}", exc_info=True)
        # Yield error event
        yield {
            "type": "error",
            "timestamp": asyncio.get_event_loop().time(),
            "payload": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        }


def reconstruct_partial_message(events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Client-side: Reconstruct partial message from event stream
    
    When the server strips the `partial` field, the client can reconstruct
    it by accumulating deltas from the event stream.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Reconstructed message with partial field
        
    Example:
        ```python
        events = []
        async for event in websocket:
            events.append(event)
            if event["type"] == "message_end":
                message = reconstruct_partial_message(events)
                break
        ```
    """
    # Accumulate content from deltas
    content_parts: list[str] = []
    thinking_parts: list[str] = []
    tool_calls: dict[str, dict[str, Any]] = {}
    
    for event in events:
        event_type = event["type"]
        payload = event.get("payload", {})
        
        if event_type == "text_delta":
            content_parts.append(payload.get("delta", ""))
        
        elif event_type == "thinking_delta":
            thinking_parts.append(payload.get("delta", ""))
        
        elif event_type == "toolcall_start":
            tool_call_id = payload.get("tool_call_id")
            if tool_call_id:
                tool_calls[tool_call_id] = {
                    "id": tool_call_id,
                    "name": payload.get("tool_name", ""),
                    "arguments": ""
                }
        
        elif event_type == "toolcall_delta":
            tool_call_id = payload.get("tool_call_id")
            if tool_call_id and tool_call_id in tool_calls:
                tool_calls[tool_call_id]["arguments"] += payload.get("delta", "")
        
        elif event_type == "toolcall_end":
            tool_call_id = payload.get("tool_call_id")
            if tool_call_id and tool_call_id in tool_calls:
                tool_calls[tool_call_id]["params"] = payload.get("params", {})
    
    # Build reconstructed message
    message = {
        "content": "".join(content_parts),
        "thinking": "".join(thinking_parts) if thinking_parts else None,
        "tool_calls": list(tool_calls.values()) if tool_calls else None,
    }
    
    return message


class StreamBuffer:
    """
    Buffer for accumulating streaming events
    
    Useful for clients that want to accumulate events before processing.
    """
    
    def __init__(self, max_size: int = 1000):
        self.events: list[dict[str, Any]] = []
        self.max_size = max_size
        self.content = ""
        self.thinking = ""
        self.tool_calls: dict[str, dict[str, Any]] = {}
    
    def add_event(self, event: dict[str, Any]) -> None:
        """Add event to buffer and update accumulators"""
        # Store event
        if len(self.events) < self.max_size:
            self.events.append(event)
        
        # Update accumulators
        event_type = event["type"]
        payload = event.get("payload", {})
        
        if event_type == "text_delta":
            self.content += payload.get("delta", "")
        
        elif event_type == "thinking_delta":
            self.thinking += payload.get("delta", "")
        
        elif event_type == "toolcall_start":
            tool_call_id = payload.get("tool_call_id")
            if tool_call_id:
                self.tool_calls[tool_call_id] = {
                    "id": tool_call_id,
                    "name": payload.get("tool_name", ""),
                    "arguments": ""
                }
        
        elif event_type == "toolcall_delta":
            tool_call_id = payload.get("tool_call_id")
            if tool_call_id and tool_call_id in self.tool_calls:
                self.tool_calls[tool_call_id]["arguments"] += payload.get("delta", "")
        
        elif event_type == "toolcall_end":
            tool_call_id = payload.get("tool_call_id")
            if tool_call_id and tool_call_id in self.tool_calls:
                self.tool_calls[tool_call_id]["params"] = payload.get("params", {})
    
    def get_current_message(self) -> dict[str, Any]:
        """Get current accumulated message"""
        return {
            "content": self.content,
            "thinking": self.thinking or None,
            "tool_calls": list(self.tool_calls.values()) if self.tool_calls else None,
        }
    
    def clear(self) -> None:
        """Clear buffer"""
        self.events.clear()
        self.content = ""
        self.thinking = ""
        self.tool_calls.clear()


async def proxy_with_buffer(
    event_stream: AsyncIterator[AgentEvent],
    buffer_size: int = 100,
) -> AsyncIterator[dict[str, Any]]:
    """
    Proxy with buffering for batched event transmission
    
    This is useful for reducing the number of network roundtrips
    by batching multiple small events together.
    
    Args:
        event_stream: AsyncIterator of AgentEvent objects
        buffer_size: Number of events to buffer before yielding
        
    Yields:
        Batches of event dictionaries
    """
    buffer: list[dict[str, Any]] = []
    
    try:
        async for event in event_stream:
            # Convert event to dict
            event_dict = {
                "type": event.type.value if hasattr(event.type, "value") else str(event.type),
                "timestamp": event.timestamp,
                "payload": event.payload.copy()
            }
            
            buffer.append(event_dict)
            
            # Yield batch if buffer is full or it's an end event
            if len(buffer) >= buffer_size or event_dict["type"] in [
                "message_end", "turn_end", "agent_end", "tool_execution_end"
            ]:
                yield {"batch": buffer}
                buffer = []
        
        # Yield remaining events
        if buffer:
            yield {"batch": buffer}
            
    except asyncio.CancelledError:
        logger.info("Buffered stream proxy cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in buffered stream proxy: {e}", exc_info=True)
        yield {
            "type": "error",
            "timestamp": asyncio.get_event_loop().time(),
            "payload": {
                "error": str(e),
                "error_type": type(e).__name__
            }
        }
