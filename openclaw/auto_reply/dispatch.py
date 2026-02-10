"""Main auto-reply dispatch system"""
from __future__ import annotations

import logging
from typing import Any

from .types import InboundMessage
from .inbound_context import finalize_inbound_context, InboundContext
from .inbound_dedupe import is_duplicate_message
from .command_detection import detect_command
from .commands_registry import get_global_command_registry

logger = logging.getLogger(__name__)


async def dispatch_inbound_message(
    message: InboundMessage,
    config: dict[str, Any] | None = None,
    runtime: Any | None = None,
) -> None:
    """
    Main dispatch entry point for inbound messages
    
    Handles:
    1. Deduplication
    2. Context normalization
    3. Command detection
    4. Reply dispatch
    
    Args:
        message: Inbound message
        config: Optional configuration
        runtime: Optional agent runtime
    """
    config = config or {}
    
    # Step 1: Finalize context
    context = finalize_inbound_context(message, config)
    
    # Step 2: Check for duplicates
    if is_duplicate_message(context.envelope):
        logger.debug(f"Skipping duplicate message: {message.message_id}")
        return
    
    # Step 3: Detect command
    command_invocation = None
    if context.text:
        command_invocation = detect_command(context.text)
    
    # Step 4: Dispatch
    if command_invocation:
        # Handle command
        await dispatch_command(command_invocation, context, config, runtime)
    else:
        # Handle regular message
        await dispatch_reply(context, config, runtime)


async def dispatch_command(
    command_invocation: Any,
    context: InboundContext,
    config: dict[str, Any],
    runtime: Any | None,
) -> None:
    """
    Dispatch command execution
    
    Args:
        command_invocation: Command invocation
        context: Inbound context
        config: Configuration
        runtime: Agent runtime
    """
    logger.info(f"Executing command: {command_invocation.command_name}")
    
    # Get command registry
    registry = get_global_command_registry()
    
    # Build command context
    cmd_context = {
        "inbound_context": context,
        "config": config,
        "runtime": runtime,
    }
    
    # Execute command
    result = await registry.execute(command_invocation, cmd_context)
    
    if result.success:
        logger.info(f"Command executed successfully: {command_invocation.command_name}")
        
        # Send result message if available
        if result.message:
            # TODO: Send message back to channel
            pass
    else:
        logger.error(f"Command execution failed: {result.error}")
        
        # TODO: Send error message back to channel


async def dispatch_reply(
    context: InboundContext,
    config: dict[str, Any],
    runtime: Any | None,
) -> None:
    """
    Dispatch reply generation
    
    Args:
        context: Inbound context
        config: Configuration
        runtime: Agent runtime
    """
    logger.info(f"Generating reply for message from {context.sender_id}")
    
    # TODO: Implement full reply dispatch
    # This requires:
    # - get_reply.py
    # - reply_dispatcher.py
    # - history.py
    # - streaming pipeline
    
    # For now, log
    logger.warning("Reply dispatch not yet fully implemented")
    
    # Placeholder: In full implementation, this would:
    # 1. Load conversation history
    # 2. Build agent prompt
    # 3. Stream agent response
    # 4. Send reply via dispatcher


async def dispatch_reply_from_config(
    context: InboundContext,
    config: dict[str, Any],
    runtime: Any | None,
) -> None:
    """
    Dispatch reply using configuration
    
    Main coordinator that:
    - Resolves agent configuration
    - Gets reply using get_reply
    - Dispatches via reply_dispatcher
    
    Args:
        context: Inbound context
        config: Configuration
        runtime: Agent runtime
    """
    # This is the main entry point that would coordinate:
    # - get_reply.py functions
    # - reply_dispatcher.py
    # - history management
    # - streaming
    
    await dispatch_reply(context, config, runtime)
