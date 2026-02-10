"""Reply dispatcher for sending messages back to channels

Handles:
- Tool result dispatch
- Block reply dispatch (streaming)
- Final reply dispatch
- Message queueing and sequencing
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """Queued outbound message"""
    
    type: str  # "tool_result", "block", "final"
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_call_id: str | None = None


class ReplyDispatcher:
    """
    Reply dispatcher for sending messages to channels
    
    Provides:
    - Message queueing
    - Streaming support
    - Tool result dispatch
    - Error handling
    """
    
    def __init__(
        self,
        channel_send_fn: Callable[[str, dict], Awaitable[Any]],
        channel_id: str,
        thread_id: str | None = None,
    ):
        """
        Initialize reply dispatcher
        
        Args:
            channel_send_fn: Function to send message to channel
            channel_id: Target channel ID
            thread_id: Optional thread ID
        """
        self.channel_send_fn = channel_send_fn
        self.channel_id = channel_id
        self.thread_id = thread_id
        
        # Message queue
        self._queue: asyncio.Queue[QueuedMessage] = asyncio.Queue()
        self._processing = False
        self._processor_task: asyncio.Task | None = None
        
        # Current message being built (for streaming)
        self._current_message = ""
        self._current_metadata: dict[str, Any] = {}
    
    async def send_tool_result(
        self,
        tool_call_id: str,
        result: str,
    ) -> None:
        """
        Send tool execution result
        
        Args:
            tool_call_id: Tool call ID
            result: Tool result
        """
        message = QueuedMessage(
            type="tool_result",
            content=result,
            tool_call_id=tool_call_id,
        )
        
        await self._queue.put(message)
        
        # Start processor if not running
        if not self._processing:
            self._start_processor()
    
    async def send_block_reply(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Send streaming block reply
        
        Accumulates text and sends when threshold reached or final.
        
        Args:
            text: Text block
            metadata: Optional metadata
        """
        self._current_message += text
        
        if metadata:
            self._current_metadata.update(metadata)
        
        # Check if we should flush (simple threshold for now)
        if len(self._current_message) >= 500:
            await self._flush_current_message()
    
    async def send_final_reply(
        self,
        text: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Send final reply
        
        Flushes any accumulated message and marks as final.
        
        Args:
            text: Optional final text
            metadata: Optional metadata
        """
        if text:
            self._current_message += text
        
        if metadata:
            self._current_metadata.update(metadata)
        
        # Flush
        await self._flush_current_message(is_final=True)
    
    async def _flush_current_message(self, is_final: bool = False) -> None:
        """Flush current accumulated message"""
        if not self._current_message:
            return
        
        message = QueuedMessage(
            type="final" if is_final else "block",
            content=self._current_message,
            metadata=self._current_metadata.copy(),
        )
        
        await self._queue.put(message)
        
        # Reset
        self._current_message = ""
        self._current_metadata = {}
        
        # Start processor if not running
        if not self._processing:
            self._start_processor()
    
    async def wait_for_idle(self) -> None:
        """Wait for all queued messages to be sent"""
        # Wait for queue to be empty
        await self._queue.join()
        
        # Wait for processor to finish
        if self._processor_task:
            await self._processor_task
    
    def _start_processor(self) -> None:
        """Start message processor task"""
        if self._processor_task and not self._processor_task.done():
            return
        
        self._processing = True
        self._processor_task = asyncio.create_task(self._process_queue())
    
    async def _process_queue(self) -> None:
        """Process message queue"""
        try:
            while True:
                try:
                    # Get message with timeout
                    message = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=0.5
                    )
                    
                    # Send message
                    await self._send_message(message)
                    
                    # Mark done
                    self._queue.task_done()
                    
                except asyncio.TimeoutError:
                    # No messages, check if we should stop
                    if self._queue.empty():
                        break
                    
        except Exception as e:
            logger.error(f"Error processing message queue: {e}", exc_info=True)
        
        finally:
            self._processing = False
    
    async def _send_message(self, message: QueuedMessage) -> None:
        """
        Send message to channel
        
        Args:
            message: Message to send
        """
        try:
            # Build send params
            params = {
                "text": message.content,
                "thread_id": self.thread_id,
                **message.metadata,
            }
            
            # Add tool_call_id if present
            if message.tool_call_id:
                params["tool_call_id"] = message.tool_call_id
            
            # Send
            await self.channel_send_fn(self.channel_id, params)
            
            logger.debug(
                f"Sent {message.type} message: "
                f"{len(message.content)} chars"
            )
            
        except Exception as e:
            logger.error(f"Error sending message: {e}", exc_info=True)
