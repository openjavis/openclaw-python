"""Slack channel plugin"""

from openclaw.channels.registry import get_channel_registry
from openclaw.channels.slack import SlackChannel


def register(api):
    """Register Slack channel"""
    channel = SlackChannel()
    registry = get_channel_registry()
    registry.register(channel)
