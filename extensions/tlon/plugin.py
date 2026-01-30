"""tlon channel plugin"""

from openclaw.channels.registry import get_channel_registry
from openclaw.channels.tlon import TlonChannel


def register(api):
    """Register tlon channel"""
    channel = TlonChannel()
    registry = get_channel_registry()
    registry.register(channel)
