"""Matrix channel plugin"""

from openclaw.channels.matrix import MatrixChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register Matrix channel"""
    channel = MatrixChannel()
    registry = get_channel_registry()
    registry.register(channel)
