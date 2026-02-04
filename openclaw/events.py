"""
Unified Event System for OpenClaw

This module provides a centralized event system that replaces
the multiple inconsistent event implementations throughout the codebase.

Architecture:
- Event: Base event class with standard fields
- EventType: Enum of all event types
- EventBus: Central event dispatcher (pub/sub pattern)

Usage:
    from openclaw.events import Event, EventType, get_event_bus

    # Subscribe
    async def on_agent_text(event: Event):
        print(f"Agent said: {event.data['text']}")

    bus = get_event_bus()
    bus.subscribe(EventType.AGENT_TEXT, on_agent_text)

    # Publish
    await bus.publish(Event(
        type=EventType.AGENT_TEXT,
        source="agent-1",
        data={"text": "Hello!"}
    ))
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================================
# Event Types
# ============================================================================


class EventType(str, Enum):
    """
    Unified event types

    Naming convention: <component>.<action>
    """

    # ========================================================================
    # Agent Events
    # ========================================================================
    AGENT_STARTED = "agent.started"
    AGENT_TEXT = "agent.text"
    AGENT_THINKING = "agent.thinking"
    AGENT_TOOL_USE = "agent.tool_use"
    AGENT_TOOL_RESULT = "agent.tool_result"
    AGENT_TURN_COMPLETE = "agent.turn_complete"
    AGENT_ERROR = "agent.error"
    AGENT_STOPPED = "agent.stopped"

    # ========================================================================
    # Channel Events
    # ========================================================================
    CHANNEL_REGISTERED = "channel.registered"
    CHANNEL_UNREGISTERED = "channel.unregistered"
    CHANNEL_STARTING = "channel.starting"
    CHANNEL_STARTED = "channel.started"
    CHANNEL_READY = "channel.ready"
    CHANNEL_STOPPING = "channel.stopping"
    CHANNEL_STOPPED = "channel.stopped"
    CHANNEL_ERROR = "channel.error"
    CHANNEL_MESSAGE_RECEIVED = "channel.message_received"
    CHANNEL_MESSAGE_SENT = "channel.message_sent"
    CHANNEL_CONNECTION_LOST = "channel.connection_lost"
    CHANNEL_RECONNECTED = "channel.reconnected"

    # ========================================================================
    # Gateway Events
    # ========================================================================
    GATEWAY_STARTED = "gateway.started"
    GATEWAY_STOPPED = "gateway.stopped"
    GATEWAY_CLIENT_CONNECTED = "gateway.client_connected"
    GATEWAY_CLIENT_DISCONNECTED = "gateway.client_disconnected"
    GATEWAY_METHOD_CALLED = "gateway.method_called"
    GATEWAY_ERROR = "gateway.error"

    # ========================================================================
    # Session Events
    # ========================================================================
    SESSION_CREATED = "session.created"
    SESSION_RESUMED = "session.resumed"
    SESSION_COMPACTED = "session.compacted"
    SESSION_CLEARED = "session.cleared"

    # ========================================================================
    # System Events
    # ========================================================================
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"


# ============================================================================
# Event Class
# ============================================================================


@dataclass
class Event:
    """
    Unified event class

    All events in OpenClaw use this standard format.

    Example:
        event = Event(
            type=EventType.AGENT_TEXT,
            source="agent-runtime-1",
            data={"text": "Hello, world!", "delta": True}
        )
    """

    # Required fields
    type: EventType
    source: str  # Component that generated the event

    # Optional fields
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    # Correlation fields (for tracing related events)
    session_id: str | None = None
    channel_id: str | None = None
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        # Handle both EventType enum and string type
        event_type = self.type.value if isinstance(self.type, EventType) else self.type
        return {
            "type": event_type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "channel_id": self.channel_id,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        return cls(
            type=EventType(data["type"]),
            source=data["source"],
            data=data.get("data", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            session_id=data.get("session_id"),
            channel_id=data.get("channel_id"),
            request_id=data.get("request_id"),
        )

    def __repr__(self) -> str:
        return f"Event(type={self.type.value}, source={self.source}, data={self.data})"


# ============================================================================
# Event Listener
# ============================================================================


EventListener = Callable[[Event], Awaitable[None]]
"""
Event listener signature

Example:
    async def my_listener(event: Event):
        print(f"Received: {event.type}")
"""


# ============================================================================
# Event Bus
# ============================================================================


class EventBus:
    """
    Central event bus for pub/sub messaging

    Features:
    - Type-safe event subscription
    - Async event dispatching
    - Multiple subscribers per event type
    - Wildcard subscriptions
    - Error handling

    Example:
        bus = EventBus()

        async def on_text(event: Event):
            print(event.data['text'])

        bus.subscribe(EventType.AGENT_TEXT, on_text)

        await bus.publish(Event(
            type=EventType.AGENT_TEXT,
            source="agent-1",
            data={"text": "Hello"}
        ))
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._listeners: dict[EventType, list[EventListener]] = defaultdict(list)
        self._wildcard_listeners: list[EventListener] = []
        self._event_count = 0
        self._error_count = 0

        logger.debug(f"EventBus '{name}' initialized")

    def subscribe(
        self,
        event_type: EventType | None,
        listener: EventListener,
    ) -> None:
        """
        Subscribe to events

        Args:
            event_type: Event type to subscribe to, or None for all events
            listener: Async function to call when event occurs

        Example:
            async def on_error(event: Event):
                logger.error(f"Error: {event.data}")

            bus.subscribe(EventType.AGENT_ERROR, on_error)

            # Subscribe to all events
            bus.subscribe(None, on_all_events)
        """
        if event_type is None:
            # Wildcard subscription (all events)
            if listener not in self._wildcard_listeners:
                self._wildcard_listeners.append(listener)
                logger.debug(f"Subscribed to ALL events: {listener.__name__}")
        else:
            if listener not in self._listeners[event_type]:
                self._listeners[event_type].append(listener)
                logger.debug(f"Subscribed to {event_type.value}: {listener.__name__}")

    def unsubscribe(
        self,
        event_type: EventType | None,
        listener: EventListener,
    ) -> bool:
        """
        Unsubscribe from events

        Args:
            event_type: Event type to unsubscribe from
            listener: Listener function to remove

        Returns:
            True if listener was removed, False if not found
        """
        if event_type is None:
            if listener in self._wildcard_listeners:
                self._wildcard_listeners.remove(listener)
                logger.debug(f"Unsubscribed from ALL events: {listener.__name__}")
                return True
        else:
            if listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)
                logger.debug(f"Unsubscribed from {event_type.value}: {listener.__name__}")
                return True

        return False

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers

        Args:
            event: Event to publish

        Example:
            await bus.publish(Event(
                type=EventType.AGENT_TEXT,
                source="agent-1",
                data={"text": "Hello!"}
            ))
        """
        self._event_count += 1

        # Get listeners for this event type
        listeners = self._listeners.get(event.type, [])

        # Add wildcard listeners
        all_listeners = listeners + self._wildcard_listeners

        if not all_listeners:
            logger.debug(f"No listeners for {event.type.value}")
            return

        logger.debug(f"Publishing {event.type.value} to {len(all_listeners)} listeners")

        # Call all listeners concurrently
        tasks = []
        for listener in all_listeners:
            tasks.append(self._call_listener_safe(listener, event))

        await asyncio.gather(*tasks)

    async def _call_listener_safe(
        self,
        listener: EventListener,
        event: Event,
    ) -> None:
        """
        Call listener with error handling

        Errors in listeners don't propagate to prevent cascading failures.
        """
        try:
            await listener(event)
        except Exception as e:
            self._error_count += 1
            logger.error(
                f"Error in event listener {listener.__name__} " f"for {event.type.value}: {e}",
                exc_info=True,
            )

    def clear(self) -> None:
        """Clear all subscriptions"""
        self._listeners.clear()
        self._wildcard_listeners.clear()
        logger.info(f"EventBus '{self.name}' cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics"""
        return {
            "name": self.name,
            "event_count": self._event_count,
            "error_count": self._error_count,
            "event_types": len(self._listeners),
            "total_listeners": sum(len(ls) for ls in self._listeners.values())
            + len(self._wildcard_listeners),
            "wildcard_listeners": len(self._wildcard_listeners),
        }

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"EventBus(name={self.name}, "
            f"listeners={stats['total_listeners']}, "
            f"events={stats['event_count']})"
        )


# ============================================================================
# Global Event Bus
# ============================================================================


_global_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance

    This is a singleton that's shared across the entire application.

    Example:
        bus = get_event_bus()
        bus.subscribe(EventType.AGENT_TEXT, my_listener)
    """
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus(name="global")
        logger.info("Global EventBus created")
    return _global_bus


def set_event_bus(bus: EventBus) -> None:
    """
    Set the global event bus instance

    Use this for testing or custom event bus implementations.
    """
    global _global_bus
    _global_bus = bus
    logger.info(f"Global EventBus set to: {bus.name}")


def reset_event_bus() -> None:
    """Reset the global event bus (mainly for testing)"""
    global _global_bus
    if _global_bus:
        _global_bus.clear()
    _global_bus = None
    logger.info("Global EventBus reset")


# ============================================================================
# Convenience Functions
# ============================================================================


async def publish(event: Event) -> None:
    """Publish event to global bus (convenience function)"""
    await get_event_bus().publish(event)


def subscribe(event_type: EventType | None, listener: EventListener) -> None:
    """Subscribe to global bus (convenience function)"""
    get_event_bus().subscribe(event_type, listener)


def unsubscribe(event_type: EventType | None, listener: EventListener) -> bool:
    """Unsubscribe from global bus (convenience function)"""
    return get_event_bus().unsubscribe(event_type, listener)
