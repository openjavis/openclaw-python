"""Type definitions for auto-reply system"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    """Message type"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    STICKER = "sticker"
    LOCATION = "location"


@dataclass
class InboundMessage:
    """Inbound message from a channel"""
    
    # Message identification
    message_id: str
    channel_id: str
    thread_id: str | None = None
    
    # Sender information
    sender_id: str
    sender_name: str | None = None
    
    # Message content
    text: str | None = None
    type: MessageType = MessageType.TEXT
    attachments: list[dict[str, Any]] = field(default_factory=list)
    
    # Context
    reply_to: str | None = None
    mentions: list[str] = field(default_factory=list)
    is_dm: bool = False
    is_group: bool = False
    
    # Metadata
    timestamp: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandInvocation:
    """Command invocation"""
    
    command_name: str
    args: list[str] = field(default_factory=list)
    kwargs: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class CommandResult:
    """Command execution result"""
    
    success: bool
    message: str = ""
    data: Any = None
    error: str | None = None


@dataclass
class ReplyContext:
    """Context for reply generation"""
    
    # Message to reply to
    inbound_message: InboundMessage
    
    # Agent configuration
    agent_id: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    
    # Reply configuration
    stream: bool = True
    max_tokens: int | None = None
    
    # History
    history_limit: int = 50
    include_history: bool = True
