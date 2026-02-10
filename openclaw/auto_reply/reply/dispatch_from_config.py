"""Dispatch reply from configuration

Main entry point that resolves configuration and calls get_reply.
"""
from __future__ import annotations

import logging
from typing import Any

from ..inbound_context import InboundContext
from .get_reply import get_reply
from .reply_dispatcher import ReplyDispatcher

logger = logging.getLogger(__name__)


async def dispatch_reply_from_config(
    context: InboundContext,
    config: dict[str, Any],
    runtime: Any,
    channel_send_fn: Any = None,
) -> None:
    """
    Dispatch reply using configuration
    
    Main coordinator that:
    - Resolves agent configuration
    - Creates reply dispatcher
    - Calls get_reply
    
    Args:
        context: Inbound context
        config: Configuration
        runtime: Agent runtime
        channel_send_fn: Optional channel send function
    """
    # Create reply dispatcher
    if channel_send_fn is None:
        # Use placeholder
        async def placeholder_send(channel_id: str, params: dict) -> None:
            logger.info(f"[PLACEHOLDER] Send to {channel_id}: {params.get('text', '')}")
        
        channel_send_fn = placeholder_send
    
    dispatcher = ReplyDispatcher(
        channel_send_fn=channel_send_fn,
        channel_id=context.channel_id,
        thread_id=context.thread_id,
    )
    
    # Get reply
    await get_reply(context, dispatcher, runtime, config)
    
    # Wait for all messages to be sent
    await dispatcher.wait_for_idle()
    
    logger.info(f"Reply dispatch complete for {context.sender_id}")
