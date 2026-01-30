"""nostr channel plugin"""

from openclaw.channels.nostr import NostrChannel
from openclaw.channels.registry import get_channel_registry


def register(api):
    """Register nostr channel"""
    channel = NostrChannel()
    registry = get_channel_registry()
    registry.register(channel)
