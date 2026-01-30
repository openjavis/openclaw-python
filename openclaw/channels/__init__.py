"""
Channel plugins for ClawdBot
"""

from .base import (
    ChannelCapabilities,
    ChannelPlugin,
    InboundMessage,
    MessageHandler,
    OutboundMessage,
)
from .connection import (
    ConnectionManager,
    ConnectionMetrics,
    ConnectionState,
    HealthChecker,
    ReconnectConfig,
)
from .discord import DiscordChannel
from .enhanced_discord import EnhancedDiscordChannel

# Enhanced versions
from .enhanced_telegram import EnhancedTelegramChannel
from .registry import ChannelRegistry, get_channel, get_channel_registry, register_channel
from .slack import SlackChannel

# Import channel implementations
from .telegram import TelegramChannel
from .webchat import WebChatChannel

__all__ = [
    # Base classes
    "ChannelPlugin",
    "ChannelCapabilities",
    "InboundMessage",
    "OutboundMessage",
    "MessageHandler",
    # Registry
    "ChannelRegistry",
    "get_channel_registry",
    "register_channel",
    "get_channel",
    # Connection management
    "ConnectionManager",
    "ConnectionState",
    "ConnectionMetrics",
    "ReconnectConfig",
    "HealthChecker",
    # Channels
    "TelegramChannel",
    "DiscordChannel",
    "SlackChannel",
    "WebChatChannel",
    "EnhancedTelegramChannel",
    "EnhancedDiscordChannel",
]
