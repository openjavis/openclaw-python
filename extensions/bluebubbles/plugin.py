"""bluebubbles channel plugin"""

from openclaw.channels.bluebubbles import BlueBubblesChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register bluebubbles channel"""
    channel = BlueBubblesChannel()
    registry = get_channel_registry()
    registry.register(channel)
