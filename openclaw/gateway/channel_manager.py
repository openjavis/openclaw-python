"""
Channel Manager - Manages channel plugins within Gateway

This implements the TypeScript OpenClaw architecture where:
- Gateway contains ChannelManager
- ChannelManager manages all channel plugins
- Each channel can have its own RuntimeEnv (Agent configuration)
- Channels connect to Agent Runtime via function calls (not HTTP/WebSocket)

Architecture:
    Gateway Server
        └── ChannelManager
                ├── Telegram Channel (plugin)
                ├── Discord Channel (plugin)
                └── ... other channels
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..agents.runtime import AgentRuntime
from ..channels.base import ChannelPlugin, InboundMessage, MessageHandler
from ..events import Event, EventType

logger = logging.getLogger(__name__)


class ChannelState(str, Enum):
    """Channel lifecycle state"""

    REGISTERED = "registered"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ChannelRuntimeEnv:
    """
    Runtime environment for a channel

    Each channel can have its own:
    - Agent Runtime (or share a default)
    - Configuration
    - Message handler

    This mirrors TypeScript's channelRuntimeEnvs concept.
    """

    channel_id: str
    agent_runtime: AgentRuntime | None = None
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    # Optional custom message handler
    custom_message_handler: MessageHandler | None = None

    # Runtime state
    state: ChannelState = ChannelState.REGISTERED
    error: str | None = None
    started_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "channel_id": self.channel_id,
            "enabled": self.enabled,
            "state": self.state.value,
            "error": self.error,
            "started_at": self.started_at,
            "has_custom_runtime": self.agent_runtime is not None,
            "has_custom_handler": self.custom_message_handler is not None,
        }


# Type for event listener callbacks
ChannelEventListener = Callable[[str, str, dict[str, Any]], Awaitable[None]]


class ChannelManager:
    """
    Manages channel plugins within Gateway

    This is the central component for channel lifecycle management,
    matching the TypeScript OpenClaw architecture.

    Features:
    - Register channel plugin classes or instances
    - Start/stop channels individually or all at once
    - Each channel can have independent configuration (RuntimeEnv)
    - Automatic message routing to Agent Runtime
    - Event emission for channel state changes

    Example:
        # Create manager with default agent runtime
        manager = ChannelManager(default_runtime=agent_runtime)

        # Register channel classes
        manager.register("telegram", EnhancedTelegramChannel)
        manager.register("discord", EnhancedDiscordChannel)

        # Configure channels
        manager.configure("telegram", {
            "bot_token": "...",
            "enabled": True
        })

        # Start specific channel
        await manager.start_channel("telegram")

        # Or start all enabled channels
        await manager.start_all()

        # Stop all
        await manager.stop_all()
    """

    def __init__(
        self,
        default_runtime: AgentRuntime | None = None,
        session_manager: Any = None,
        tools: list | None = None,
        system_prompt: str | None = None,
    ):
        """
        Initialize ChannelManager

        Args:
            default_runtime: Default AgentRuntime for channels that don't have their own
            session_manager: Session manager for creating/retrieving sessions
            tools: List of tools available to the agent
            system_prompt: Optional system prompt (skills, capabilities, etc.)
        """
        self.default_runtime = default_runtime
        self.session_manager = session_manager
        self.tools = tools or []
        self.system_prompt = system_prompt

        # Channel plugin classes (for lazy instantiation)
        self._channel_classes: dict[str, type[ChannelPlugin]] = {}

        # Channel plugin instances
        self._channels: dict[str, ChannelPlugin] = {}

        # Runtime environments per channel
        self._runtime_envs: dict[str, ChannelRuntimeEnv] = {}

        # Event listeners
        self._event_listeners: list[ChannelEventListener] = []

        # Running state
        self._running = False

        logger.info("ChannelManager initialized")

    # =========================================================================
    # Registration
    # =========================================================================

    def register(
        self,
        channel_id: str,
        channel_class: type[ChannelPlugin],
        config: dict[str, Any] | None = None,
        runtime: AgentRuntime | None = None,
    ) -> None:
        """
        Register a channel plugin class

        The channel will be instantiated lazily when needed.

        Args:
            channel_id: Unique identifier for the channel
            channel_class: Channel plugin class
            config: Optional initial configuration
            runtime: Optional custom AgentRuntime for this channel
        """
        self._channel_classes[channel_id] = channel_class

        # Create runtime environment
        self._runtime_envs[channel_id] = ChannelRuntimeEnv(
            channel_id=channel_id,
            agent_runtime=runtime,
            config=config or {},
            enabled=True,
        )

        logger.info(f"Registered channel class: {channel_id}")
        asyncio.create_task(self._emit_event("registered", channel_id, {}))

    def register_instance(
        self,
        channel: ChannelPlugin,
        config: dict[str, Any] | None = None,
        runtime: AgentRuntime | None = None,
    ) -> None:
        """
        Register a channel plugin instance directly

        Args:
            channel: Channel plugin instance
            config: Optional initial configuration
            runtime: Optional custom AgentRuntime for this channel
        """
        if not channel.id:
            raise ValueError("Channel must have an ID")

        self._channels[channel.id] = channel

        # Create runtime environment
        self._runtime_envs[channel.id] = ChannelRuntimeEnv(
            channel_id=channel.id,
            agent_runtime=runtime,
            config=config or {},
            enabled=True,
        )

        logger.info(f"Registered channel instance: {channel.id}")
        asyncio.create_task(self._emit_event("registered", channel.id, {}))

    def unregister(self, channel_id: str) -> bool:
        """
        Unregister a channel

        The channel will be stopped if running.

        Args:
            channel_id: Channel to unregister

        Returns:
            True if unregistered, False if not found
        """
        if channel_id not in self._channel_classes and channel_id not in self._channels:
            return False

        # Remove from all registries
        self._channel_classes.pop(channel_id, None)
        self._channels.pop(channel_id, None)
        self._runtime_envs.pop(channel_id, None)

        logger.info(f"Unregistered channel: {channel_id}")
        asyncio.create_task(self._emit_event("unregistered", channel_id, {}))
        return True

    # =========================================================================
    # Configuration
    # =========================================================================

    def configure(
        self,
        channel_id: str,
        config: dict[str, Any],
        merge: bool = True,
    ) -> None:
        """
        Configure a channel

        Args:
            channel_id: Channel to configure
            config: Configuration dictionary
            merge: If True, merge with existing config; otherwise replace
        """
        if channel_id not in self._runtime_envs:
            # Auto-create runtime env if channel class exists
            if channel_id in self._channel_classes:
                self._runtime_envs[channel_id] = ChannelRuntimeEnv(channel_id=channel_id)
            else:
                raise ValueError(f"Channel not registered: {channel_id}")

        env = self._runtime_envs[channel_id]

        if merge:
            env.config.update(config)
        else:
            env.config = config

        # Handle special config keys
        if "enabled" in config:
            env.enabled = config["enabled"]

        logger.debug(f"Configured channel {channel_id}: {config}")

    def set_runtime(self, channel_id: str, runtime: AgentRuntime) -> None:
        """
        Set custom AgentRuntime for a channel

        Args:
            channel_id: Channel ID
            runtime: Custom AgentRuntime
        """
        if channel_id not in self._runtime_envs:
            raise ValueError(f"Channel not registered: {channel_id}")

        self._runtime_envs[channel_id].agent_runtime = runtime
        logger.info(f"Set custom runtime for channel: {channel_id}")

    def set_message_handler(self, channel_id: str, handler: MessageHandler) -> None:
        """
        Set custom message handler for a channel

        This overrides the default Agent Runtime handler.

        Args:
            channel_id: Channel ID
            handler: Custom message handler
        """
        if channel_id not in self._runtime_envs:
            raise ValueError(f"Channel not registered: {channel_id}")

        self._runtime_envs[channel_id].custom_message_handler = handler
        logger.info(f"Set custom message handler for channel: {channel_id}")

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    async def start_channel(self, channel_id: str) -> bool:
        """
        Start a specific channel

        Args:
            channel_id: Channel to start

        Returns:
            True if started successfully
        """
        env = self._runtime_envs.get(channel_id)
        if not env:
            logger.error(f"Channel not found: {channel_id}")
            return False

        if not env.enabled:
            logger.info(f"Channel disabled, skipping: {channel_id}")
            return False

        # Get or create channel instance
        channel = self._get_or_create_channel(channel_id)
        if not channel:
            return False

        try:
            env.state = ChannelState.STARTING
            await self._emit_event("starting", channel_id, {})

            # Set up message handler
            handler = self._create_message_handler(channel_id)
            channel.set_message_handler(handler)

            # Start channel with config
            await channel.start(env.config)

            env.state = ChannelState.RUNNING
            env.error = None

            from datetime import datetime

            env.started_at = datetime.now().isoformat()

            logger.info(f"✅ Channel started: {channel_id}")
            await self._emit_event("started", channel_id, {})
            return True

        except Exception as e:
            env.state = ChannelState.ERROR
            env.error = str(e)
            logger.error(f"❌ Failed to start channel {channel_id}: {e}")
            await self._emit_event("error", channel_id, {"error": str(e)})
            return False

    async def stop_channel(self, channel_id: str) -> bool:
        """
        Stop a specific channel

        Args:
            channel_id: Channel to stop

        Returns:
            True if stopped successfully
        """
        channel = self._channels.get(channel_id)
        if not channel:
            logger.warning(f"Channel not found or not started: {channel_id}")
            return False

        env = self._runtime_envs.get(channel_id)
        if env:
            env.state = ChannelState.STOPPING

        await self._emit_event("stopping", channel_id, {})

        try:
            await channel.stop()

            if env:
                env.state = ChannelState.STOPPED

            logger.info(f"Channel stopped: {channel_id}")
            await self._emit_event("stopped", channel_id, {})
            return True

        except Exception as e:
            if env:
                env.state = ChannelState.ERROR
                env.error = str(e)
            logger.error(f"Failed to stop channel {channel_id}: {e}")
            await self._emit_event("error", channel_id, {"error": str(e)})
            return False

    async def restart_channel(self, channel_id: str) -> bool:
        """
        Restart a channel

        Args:
            channel_id: Channel to restart

        Returns:
            True if restarted successfully
        """
        await self.stop_channel(channel_id)
        return await self.start_channel(channel_id)

    async def start_all(self) -> dict[str, bool]:
        """
        Start all enabled channels

        Returns:
            Dict mapping channel_id to success status
        """
        self._running = True
        results = {}

        for channel_id, env in self._runtime_envs.items():
            if env.enabled:
                results[channel_id] = await self.start_channel(channel_id)

        return results

    async def stop_all(self) -> None:
        """Stop all running channels"""
        self._running = False

        for channel_id, channel in list(self._channels.items()):
            if channel.is_running():
                await self.stop_channel(channel_id)

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_channel(self, channel_id: str) -> ChannelPlugin | None:
        """Get channel instance by ID"""
        return self._channels.get(channel_id)

    def get_runtime_env(self, channel_id: str) -> ChannelRuntimeEnv | None:
        """Get runtime environment for a channel"""
        return self._runtime_envs.get(channel_id)

    def get_runtime(self, channel_id: str) -> AgentRuntime | None:
        """
        Get AgentRuntime for a channel

        Returns channel-specific runtime if set, otherwise default runtime.
        """
        env = self._runtime_envs.get(channel_id)
        if env and env.agent_runtime:
            return env.agent_runtime
        return self.default_runtime

    def list_channels(self) -> list[str]:
        """List all registered channel IDs"""
        all_ids = set(self._channel_classes.keys())
        all_ids.update(self._channels.keys())
        return sorted(all_ids)

    def list_running(self) -> list[str]:
        """List running channel IDs"""
        return [ch_id for ch_id, ch in self._channels.items() if ch.is_running()]

    def list_enabled(self) -> list[str]:
        """List enabled channel IDs"""
        return [ch_id for ch_id, env in self._runtime_envs.items() if env.enabled]

    def get_status(self, channel_id: str) -> dict[str, Any] | None:
        """Get channel status"""
        channel = self._channels.get(channel_id)
        env = self._runtime_envs.get(channel_id)

        if not env:
            return None

        result = env.to_dict()

        if channel:
            result.update(
                {
                    "running": channel.is_running(),
                    "connected": channel.is_connected(),
                    "healthy": channel.is_healthy(),
                    "label": channel.label,
                    "capabilities": channel.capabilities.model_dump(),
                }
            )

            metrics = channel.get_metrics()
            if metrics:
                result["metrics"] = metrics.to_dict()

        return result

    def get_all_status(self) -> dict[str, Any]:
        """Get status of all channels"""
        channels = {}
        for channel_id in self.list_channels():
            status = self.get_status(channel_id)
            if status:
                channels[channel_id] = status

        return {
            "running": self._running,
            "total": len(channels),
            "running_count": len(self.list_running()),
            "enabled_count": len(self.list_enabled()),
            "channels": channels,
        }

    # =========================================================================
    # Event System
    # =========================================================================

    def add_event_listener(self, listener: ChannelEventListener) -> None:
        """Add event listener for channel events"""
        self._event_listeners.append(listener)

    def remove_event_listener(self, listener: ChannelEventListener) -> None:
        """Remove event listener"""
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)

    async def _emit_event(
        self,
        event_type_str: str,
        channel_id: str,
        data: dict[str, Any],
    ) -> None:
        """
        Emit channel event to all listeners using unified Event system

        Args:
            event_type_str: String event type (e.g., "registered", "started")
            channel_id: Channel ID
            data: Event data
        """
        # Map string event type to EventType enum
        event_type_map = {
            "registered": EventType.CHANNEL_REGISTERED,
            "unregistered": EventType.CHANNEL_UNREGISTERED,
            "starting": EventType.CHANNEL_STARTING,
            "started": EventType.CHANNEL_STARTED,
            "ready": EventType.CHANNEL_READY,
            "stopping": EventType.CHANNEL_STOPPING,
            "stopped": EventType.CHANNEL_STOPPED,
            "error": EventType.CHANNEL_ERROR,
        }

        event_type = event_type_map.get(event_type_str, EventType.CHANNEL_ERROR)

        # Create unified Event
        event = Event(type=event_type, source="channel-manager", channel_id=channel_id, data=data)

        # Notify legacy listeners (for backward compatibility)
        for listener in self._event_listeners:
            try:
                await listener(event_type_str, channel_id, data)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _get_or_create_channel(self, channel_id: str) -> ChannelPlugin | None:
        """Get existing channel or create from class"""
        if channel_id in self._channels:
            return self._channels[channel_id]

        if channel_id in self._channel_classes:
            channel_class = self._channel_classes[channel_id]
            channel = channel_class()
            self._channels[channel_id] = channel
            return channel

        return None

    def _create_message_handler(self, channel_id: str) -> MessageHandler:
        """
        Create message handler for a channel

        This is where the magic happens:
        - Gets the appropriate AgentRuntime (channel-specific or default)
        - Creates a handler that processes messages through the Agent
        - Sends responses back via the channel
        """

        async def handler(message: InboundMessage) -> None:
            env = self._runtime_envs.get(channel_id)

            # Check for custom handler first
            if env and env.custom_message_handler:
                await env.custom_message_handler(message)
                return

            # Get runtime
            runtime = self.get_runtime(channel_id)
            if not runtime:
                logger.error(f"No AgentRuntime available for channel: {channel_id}")
                return

            # Get channel for sending response
            channel = self._channels.get(channel_id)
            if not channel:
                logger.error(f"Channel not found: {channel_id}")
                return

            logger.info(f"📨 [{channel_id}] Message from {message.sender_name}: {message.text}")

            try:
                # Get or create session
                session_id = f"{channel_id}-{message.chat_id}"
                session = None

                if self.session_manager:
                    session = self.session_manager.get_session(session_id)
                    logger.info(f"[{channel_id}] Session created/retrieved: {session_id}")

                # Process through Agent Runtime
                response_text = ""
                logger.info(f"[{channel_id}] Starting runtime.run_turn with {len(self.tools)} tools")

                # Extract photo URL from metadata if present
                images = None
                if message.metadata and message.metadata.get("photo_url"):
                    images = [message.metadata["photo_url"]]
                    logger.info(f"[{channel_id}] Including photo in request: {images[0][:80]}...")

                async for event in runtime.run_turn(
                    session, 
                    message.text, 
                    tools=self.tools, 
                    images=images,
                    system_prompt=self.system_prompt
                ):
                    event_type_str = str(getattr(event, 'type', 'unknown'))
                    logger.debug(f"[{channel_id}] Event received: type={event_type_str}")
                    if hasattr(event, "type"):
                        # Handle EventType enum or string
                        event_type_value = event.type.value if hasattr(event.type, 'value') else str(event.type)
                        
                        if event_type_value == "agent.text" or event_type_value == "text":
                            delta_text = event.data.get("delta", {}).get("text", "")
                            response_text += delta_text
                            logger.debug(f"[{channel_id}] Text delta: {delta_text[:50]}...")
                        elif event_type_value == "agent.turn_complete" or event_type_value == "turn_complete":
                            logger.info(f"[{channel_id}] Turn complete")
                            break
                    elif isinstance(event, dict):
                        if event.get("type") == "text":
                            response_text += event.get("text", "")
                        elif event.get("type") == "turn_complete":
                            break

                logger.info(f"[{channel_id}] Accumulated response length: {len(response_text)}")

                # Send response back
                if response_text:
                    await channel.send_text(
                        target=message.chat_id,
                        text=response_text,
                        reply_to=message.message_id,
                    )
                    logger.info(f"📤 [{channel_id}] Sent response to {message.chat_id}")
                else:
                    logger.warning(f"[{channel_id}] No response text generated")

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                # Optionally send error message
                try:
                    await channel.send_text(
                        target=message.chat_id,
                        text=f"Sorry, I encountered an error: {str(e)[:100]}",
                    )
                except Exception:
                    pass

        return handler

    def to_dict(self) -> dict[str, Any]:
        """Convert manager to dictionary"""
        return self.get_all_status()


# ============================================================================
# Plugin Discovery
# ============================================================================


def discover_channel_plugins() -> dict[str, type[ChannelPlugin]]:
    """
    Discover available channel plugin classes

    This scans the channels module and returns all available plugin classes.

    Returns:
        Dict mapping channel_id to plugin class
    """
    from ..channels import (
        DiscordChannel,
        EnhancedDiscordChannel,
        EnhancedTelegramChannel,
        SlackChannel,
        TelegramChannel,
        WebChatChannel,
    )

    # Try to import optional channels
    plugins: dict[str, type[ChannelPlugin]] = {}

    # Core channels (always available)
    core_channels = [
        ("telegram", TelegramChannel),
        ("telegram-enhanced", EnhancedTelegramChannel),
        ("discord", DiscordChannel),
        ("discord-enhanced", EnhancedDiscordChannel),
        ("slack", SlackChannel),
        ("webchat", WebChatChannel),
    ]

    for channel_id, channel_class in core_channels:
        try:
            # Verify it's a valid channel
            instance = channel_class()
            actual_id = instance.id or channel_id
            plugins[actual_id] = channel_class
            logger.debug(f"Discovered channel plugin: {actual_id}")
        except Exception as e:
            logger.debug(f"Could not load channel {channel_id}: {e}")

    # Try to load additional optional channels
    optional_channels = [
        ("whatsapp", "WhatsAppChannel"),
        ("signal", "SignalChannel"),
        ("matrix", "MatrixChannel"),
        ("teams", "TeamsChannel"),
        ("line", "LineChannel"),
        ("imessage", "iMessageChannel"),
    ]

    for channel_id, class_name in optional_channels:
        try:
            module = __import__(f"openclaw.channels.{channel_id}", fromlist=[class_name])
            channel_class = getattr(module, class_name, None)
            if channel_class:
                instance = channel_class()
                actual_id = instance.id or channel_id
                plugins[actual_id] = channel_class
                logger.debug(f"Discovered optional channel: {actual_id}")
        except Exception:
            pass  # Optional channel not available

    return plugins


def load_channel_plugins(
    config: dict[str, Any] | None = None,
) -> dict[str, type[ChannelPlugin]]:
    """
    Load channel plugins based on configuration

    Args:
        config: Optional config dict with channel settings
               {"channels": {"telegram": {"enabled": true}, ...}}

    Returns:
        Dict of enabled channel plugins
    """
    all_plugins = discover_channel_plugins()

    if not config:
        return all_plugins

    # Filter by config
    channels_config = config.get("channels", {})

    enabled_plugins = {}
    for channel_id, plugin_class in all_plugins.items():
        channel_config = channels_config.get(channel_id, {})

        # Default to enabled if not specified
        if channel_config.get("enabled", True):
            enabled_plugins[channel_id] = plugin_class

    return enabled_plugins
