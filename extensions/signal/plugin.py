"""Signal channel plugin"""

from openclaw.channels.registry import get_channel_registry
from openclaw.channels.signal import SignalChannel


def register(api):
    """Register Signal channel"""
    channel = SignalChannel()
    registry = get_channel_registry()
    registry.register(channel)
