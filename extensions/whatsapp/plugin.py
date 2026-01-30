"""WhatsApp channel plugin"""

from openclaw.channels.registry import get_channel_registry
from openclaw.channels.whatsapp import WhatsAppChannel


def register(api):
    """Register WhatsApp channel"""
    channel = WhatsAppChannel()
    registry = get_channel_registry()
    registry.register(channel)
