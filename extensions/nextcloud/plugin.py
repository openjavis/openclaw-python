"""nextcloud channel plugin"""

from openclaw.channels.nextcloud import NextcloudChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register nextcloud channel"""
    channel = NextcloudChannel()
    registry = get_channel_registry()
    registry.register(channel)
