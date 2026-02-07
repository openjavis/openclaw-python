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

# Enhanced / optional channels - import if available
try:
    from .enhanced_discord import EnhancedDiscordChannel
except Exception:
    EnhancedDiscordChannel = None

try:
    from .enhanced_telegram import EnhancedTelegramChannel
except Exception:
    EnhancedTelegramChannel = None

from .registry import ChannelRegistry, get_channel, get_channel_registry, register_channel

try:
    from .slack import SlackChannel
except Exception:
    SlackChannel = None

# Import channel implementations
try:
    from .telegram import TelegramChannel
except Exception:
    TelegramChannel = None

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
