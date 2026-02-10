"""Inbound message context normalization"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .types import InboundMessage
from .envelope import InboundEnvelope

logger = logging.getLogger(__name__)


@dataclass
class InboundContext:
    """
    Normalized inbound message context
    
    Provides unified interface for message processing across all channels.
    """
    
    # Message
    envelope: InboundEnvelope
    
    # Normalized sender
    sender_id: str
    sender_name: str
    sender_handle: str | None = None
    
    # Normalized target
    channel_id: str
    thread_id: str | None = None
    
    # Chat context
    is_dm: bool = False
    is_group: bool = False
    group_name: str | None = None
    
    # Message content
    text: str = ""
    has_attachments: bool = False
    
    # Mentions and references
    mentions: list[str] = field(default_factory=list)
    reply_to: str | None = None
    
    # Agent configuration
    agent_id: str | None = None
    force_agent: bool = False
    
    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


def finalize_inbound_context(
    message: InboundMessage,
    config: dict[str, Any] | None = None
) -> InboundContext:
    """
    Finalize inbound context from message
    
    Normalizes message data into InboundContext for consistent processing.
    
    Args:
        message: Inbound message
        config: Optional configuration
        
    Returns:
        Normalized context
    """
    config = config or {}
    
    # Create envelope
    envelope = InboundEnvelope(message=message)
    
    # Normalize sender
    sender_id = message.sender_id
    sender_name = message.sender_name or message.sender_id
    sender_handle = _extract_handle(sender_name)
    
    # Normalize target
    channel_id = message.channel_id
    thread_id = message.thread_id
    
    # Chat type
    is_dm = message.is_dm
    is_group = message.is_group
    
    # Content
    text = (message.text or "").strip()
    has_attachments = len(message.attachments) > 0
    
    # Mentions
    mentions = message.mentions or []
    reply_to = message.reply_to
    
    # Agent configuration
    agent_id = config.get("agent_id")
    force_agent = config.get("force_agent", False)
    
    # Build context
    context = InboundContext(
        envelope=envelope,
        sender_id=sender_id,
        sender_name=sender_name,
        sender_handle=sender_handle,
        channel_id=channel_id,
        thread_id=thread_id,
        is_dm=is_dm,
        is_group=is_group,
        text=text,
        has_attachments=has_attachments,
        mentions=mentions,
        reply_to=reply_to,
        agent_id=agent_id,
        force_agent=force_agent,
        metadata=config.get("metadata", {}),
    )
    
    logger.debug(
        f"Finalized context: channel={channel_id}, "
        f"sender={sender_id}, is_dm={is_dm}, text_len={len(text)}"
    )
    
    return context


def _extract_handle(name: str) -> str | None:
    """Extract handle from name (e.g., @username)"""
    if not name:
        return None
    
    # Check for @username pattern
    if name.startswith("@"):
        return name[1:]
    
    # Check if name contains @ symbol
    if "@" in name:
        parts = name.split("@")
        if len(parts) == 2:
            return parts[1]
    
    return None
