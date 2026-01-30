"""
Channel registry for managing channel plugins
"""

import logging

from .base import ChannelPlugin

logger = logging.getLogger(__name__)


class ChannelRegistry:
    """
    Registry for managing channel plugins

    Example:
        registry = ChannelRegistry()
        registry.register(TelegramChannel())
        registry.register(DiscordChannel())

        telegram = registry.get("telegram")
        await telegram.start(config)
    """

    def __init__(self):
        self._channels: dict[str, ChannelPlugin] = {}
        self._channel_classes: dict[str, type[ChannelPlugin]] = {}

    def register(self, channel: ChannelPlugin) -> None:
        """
        Register a channel plugin instance

        Args:
            channel: Channel plugin instance
        """
        if not channel.id:
            raise ValueError("Channel must have an ID")

        self._channels[channel.id] = channel
        logger.info(f"Registered channel: {channel.id} ({channel.label})")

    def register_class(self, channel_class: type[ChannelPlugin]) -> None:
        """
        Register a channel plugin class (lazy instantiation)

        Args:
            channel_class: Channel plugin class
        """
        instance = channel_class()
        self._channel_classes[instance.id] = channel_class
        logger.info(f"Registered channel class: {instance.id}")

    def get(self, channel_id: str) -> ChannelPlugin | None:
        """
        Get a channel plugin by ID

        Args:
            channel_id: Channel identifier

        Returns:
            Channel plugin or None
        """
        # Check if already instantiated
        if channel_id in self._channels:
            return self._channels[channel_id]

        # Try to instantiate from class
        if channel_id in self._channel_classes:
            channel = self._channel_classes[channel_id]()
            self._channels[channel_id] = channel
            return channel

        return None

    def get_all(self) -> list[ChannelPlugin]:
        """
        Get all registered channels

        Returns:
            List of channel plugins
        """
        return list(self._channels.values())

    def list_ids(self) -> list[str]:
        """
        List all registered channel IDs

        Returns:
            List of channel IDs
        """
        all_ids = set(self._channels.keys())
        all_ids.update(self._channel_classes.keys())
        return sorted(all_ids)

    def unregister(self, channel_id: str) -> bool:
        """
        Unregister a channel

        Args:
            channel_id: Channel to unregister

        Returns:
            True if unregistered, False if not found
        """
        removed = False

        if channel_id in self._channels:
            del self._channels[channel_id]
            removed = True

        if channel_id in self._channel_classes:
            del self._channel_classes[channel_id]
            removed = True

        if removed:
            logger.info(f"Unregistered channel: {channel_id}")

        return removed

    def get_running(self) -> list[ChannelPlugin]:
        """
        Get all running channels

        Returns:
            List of running channel plugins
        """
        return [ch for ch in self._channels.values() if ch.is_running()]

    def get_by_capability(self, capability: str) -> list[ChannelPlugin]:
        """
        Get channels with a specific capability

        Args:
            capability: Capability name (e.g., "supports_media")

        Returns:
            List of channels with that capability
        """
        result = []
        for channel in self._channels.values():
            caps = channel.capabilities
            if getattr(caps, capability, False):
                result.append(channel)
        return result

    async def start_all(self, configs: dict[str, dict]) -> dict[str, bool]:
        """
        Start all channels with provided configs

        Args:
            configs: Dict mapping channel_id to config

        Returns:
            Dict mapping channel_id to success status
        """
        results = {}

        for channel_id, config in configs.items():
            channel = self.get(channel_id)
            if not channel:
                results[channel_id] = False
                continue

            try:
                await channel.start(config)
                results[channel_id] = True
            except Exception as e:
                logger.error(f"Failed to start {channel_id}: {e}")
                results[channel_id] = False

        return results

    async def stop_all(self) -> None:
        """Stop all running channels"""
        for channel in self.get_running():
            try:
                await channel.stop()
            except Exception as e:
                logger.error(f"Failed to stop {channel.id}: {e}")

    def to_dict(self) -> dict:
        """Convert registry to dictionary"""
        return {
            "channels": [ch.to_dict() for ch in self._channels.values()],
            "registered_classes": list(self._channel_classes.keys()),
            "running_count": len(self.get_running()),
            "total_count": len(self._channels),
        }


# Global registry instance
_registry: ChannelRegistry | None = None


def get_channel_registry() -> ChannelRegistry:
    """Get global channel registry"""
    global _registry
    if _registry is None:
        _registry = ChannelRegistry()
    return _registry


def register_channel(channel: ChannelPlugin) -> None:
    """Register channel with global registry"""
    get_channel_registry().register(channel)


def get_channel(channel_id: str) -> ChannelPlugin | None:
    """Get channel from global registry"""
    return get_channel_registry().get(channel_id)
