"""imessage channel plugin"""

from openclaw.channels.imessage import iMessageChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register imessage channel"""
    channel = iMessageChannel()
    registry = get_channel_registry()
    registry.register(channel)
