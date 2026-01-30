"""mattermost channel plugin"""

from openclaw.channels.mattermost import MattermostChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register mattermost channel"""
    channel = MattermostChannel()
    registry = get_channel_registry()
    registry.register(channel)
