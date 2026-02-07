"""Message processing pipeline.

Processes inbound messages and determines responses.
Aligned with TypeScript src/web/auto-reply/monitor/process-message.ts
"""

from __future__ import annotations

from dataclasses import dataclass

from openclaw.auto_reply.reply import get_reply
from openclaw.auto_reply.types import GetReplyOptions, ReplyPayload

from .group_gating import should_process_group_message
from .mentions import strip_mentions


@dataclass
class ProcessedMessage:
    """Result of message processing."""

    should_reply: bool  # Whether to send a reply
    reply_payload: ReplyPayload | None = None  # Reply to send
    reason: str | None = None  # Reason for decision


async def process_message(
    session_key: str,
    message_text: str,
    is_group: bool = False,
    config: dict | None = None,
    reply_options: GetReplyOptions | None = None,
) -> ProcessedMessage:
    """Process an inbound message.

    Main entry point for message processing pipeline.

    Args:
        session_key: Session key for routing
        message_text: Message text
        is_group: Whether this is a group message
        config: Optional configuration
        reply_options: Optional reply options

    Returns:
        ProcessedMessage with decision and reply
    """
    # Check group gating
    if is_group:
        if not should_process_group_message(message_text, is_group, config):
            return ProcessedMessage(should_reply=False, reason="group_gating_failed")

    # Strip mentions from message
    cleaned_message = strip_mentions(message_text)

    if not cleaned_message.strip():
        return ProcessedMessage(should_reply=False, reason="empty_message")

    try:
        # Get reply from agent
        reply = await get_reply(
            session_key=session_key, user_message=cleaned_message, options=reply_options
        )

        if not reply:
            return ProcessedMessage(should_reply=False, reason="no_reply")

        # Handle list of replies
        if isinstance(reply, list):
            if len(reply) == 0:
                return ProcessedMessage(should_reply=False, reason="empty_reply_list")
            reply = reply[0]  # Use first reply

        return ProcessedMessage(should_reply=True, reply_payload=reply, reason="success")

    except Exception as e:
        # Return error
        return ProcessedMessage(
            should_reply=True,
            reply_payload=ReplyPayload(text=f"Error processing message: {str(e)}", is_error=True),
            reason="error",
        )


async def process_and_send(
    session_key: str,
    message_text: str,
    is_group: bool = False,
    config: dict | None = None,
    reply_options: GetReplyOptions | None = None,
    send_callback: callable | None = None,
) -> bool:
    """Process message and send reply.

    Higher-level helper that processes message and sends reply.

    Args:
        session_key: Session key
        message_text: Message text
        is_group: Whether this is a group
        config: Configuration
        reply_options: Reply options
        send_callback: Callback to send reply (async function)

    Returns:
        True if reply was sent
    """
    result = await process_message(
        session_key=session_key,
        message_text=message_text,
        is_group=is_group,
        config=config,
        reply_options=reply_options,
    )

    if not result.should_reply or not result.reply_payload:
        return False

    if send_callback:
        await send_callback(result.reply_payload)
        return True

    return False
