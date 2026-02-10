"""Get reply - coordinates reply generation

Main coordination for:
- Loading history
- Building agent prompt
- Streaming agent response
- Dispatching replies
"""
from __future__ import annotations

import logging
from typing import Any

from ..inbound_context import InboundContext
from .history import get_global_history
from .reply_dispatcher import ReplyDispatcher

logger = logging.getLogger(__name__)


async def get_reply(
    context: InboundContext,
    dispatcher: ReplyDispatcher,
    runtime: Any,
    config: dict[str, Any] | None = None,
) -> None:
    """
    Get reply for inbound message
    
    Main coordinator that:
    1. Loads conversation history
    2. Builds agent prompt with history
    3. Streams agent response
    4. Dispatches reply blocks
    
    Args:
        context: Inbound context
        dispatcher: Reply dispatcher
        runtime: Agent runtime
        config: Optional configuration
    """
    config = config or {}
    
    # Get history
    history = get_global_history()
    
    # Load session history
    history_entries = history.get_history(
        channel_id=context.channel_id,
        sender_id=context.sender_id,
        thread_id=context.thread_id,
        limit=config.get("history_limit", 50),
    )
    
    logger.info(
        f"Loaded {len(history_entries)} history messages "
        f"for {context.sender_id}"
    )
    
    # Build messages for agent
    messages = []
    
    # Add history
    for entry in history_entries:
        messages.append({
            "role": entry.role,
            "content": entry.content,
        })
    
    # Add current message
    messages.append({
        "role": "user",
        "content": context.text,
    })
    
    # Add current message to history
    history.add_message(
        channel_id=context.channel_id,
        sender_id=context.sender_id,
        role="user",
        content=context.text,
        thread_id=context.thread_id,
        is_group=context.is_group,
    )
    
    # Get agent configuration
    model = config.get("model", "gpt-4")
    system_prompt = config.get("system_prompt")
    
    # Stream agent response
    response_text = ""
    
    try:
        # TODO: Replace with actual agent runtime streaming
        # For now, this is a placeholder
        
        # In full implementation:
        # async for event in runtime.stream_chat(messages, model, system_prompt):
        #     if event.type == "text":
        #         response_text += event.content
        #         await dispatcher.send_block_reply(event.content)
        
        # Placeholder response
        response_text = f"Received: {context.text}"
        await dispatcher.send_block_reply(response_text)
        
    except Exception as e:
        logger.error(f"Error streaming agent response: {e}", exc_info=True)
        error_msg = "Sorry, I encountered an error processing your message."
        await dispatcher.send_block_reply(error_msg)
        response_text = error_msg
    
    # Send final
    await dispatcher.send_final_reply()
    
    # Add assistant response to history
    history.add_message(
        channel_id=context.channel_id,
        sender_id=context.sender_id,
        role="assistant",
        content=response_text,
        thread_id=context.thread_id,
        is_group=context.is_group,
    )
    
    logger.info(f"Completed reply for {context.sender_id}")
