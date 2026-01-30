"""line channel plugin"""

from openclaw.channels.line import LINEChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register line channel"""
    channel = LINEChannel()
    registry = get_channel_registry()
    registry.register(channel)
