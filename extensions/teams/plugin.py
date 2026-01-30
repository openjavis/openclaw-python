"""teams channel plugin"""

from openclaw.channels.registry import get_channel_registry
from openclaw.channels.teams import TeamsChannel


def register(api):
    """Register teams channel"""
    channel = TeamsChannel()
    registry = get_channel_registry()
    registry.register(channel)
