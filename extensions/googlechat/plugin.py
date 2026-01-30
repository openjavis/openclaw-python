"""Google Chat channel plugin"""

from openclaw.channels.googlechat import GoogleChatChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register Google Chat channel"""
    channel = GoogleChatChannel()
    registry = get_channel_registry()
    registry.register(channel)
