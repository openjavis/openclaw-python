"""
Example 12: Unified Event System Demo

This example demonstrates the new unified event system that will
replace multiple inconsistent event implementations.

Features:
- Type-safe event types
- Centralized EventBus
- Async event dispatching
- Multiple subscribers
- Wildcard subscriptions

Usage:
    uv run python examples/12_event_system_demo.py
"""

import asyncio
import logging

from openclaw.events import Event, EventBus, EventType, get_event_bus
from openclaw.monitoring import setup_logging

logger = logging.getLogger(__name__)


async def demo_basic_events():
    """Demonstrate basic event pub/sub"""
    print("=" * 60)
    print("1️⃣ Basic Event Publishing & Subscription")
    print("=" * 60)
    print()

    # Get the global event bus
    bus = get_event_bus()

    # Define event listeners
    async def on_agent_text(event: Event):
        text = event.data.get("text", "")
        print(f"📝 Agent said: {text}")

    async def on_agent_thinking(event: Event):
        thought = event.data.get("thought", "")
        print(f"🤔 Agent thinking: {thought}")

    # Subscribe to specific events
    bus.subscribe(EventType.AGENT_TEXT, on_agent_text)
    bus.subscribe(EventType.AGENT_THINKING, on_agent_thinking)

    # Publish events
    await bus.publish(
        Event(
            type=EventType.AGENT_TEXT,
            source="demo-agent",
            data={"text": "Hello, I'm the AI assistant!"},
        )
    )

    await bus.publish(
        Event(
            type=EventType.AGENT_THINKING,
            source="demo-agent",
            data={"thought": "Let me think about this problem..."},
        )
    )

    await bus.publish(
        Event(type=EventType.AGENT_TEXT, source="demo-agent", data={"text": "The answer is 42."})
    )

    print()


async def demo_wildcard_subscription():
    """Demonstrate wildcard subscriptions"""
    print("=" * 60)
    print("2️⃣ Wildcard Subscription (Listen to All Events)")
    print("=" * 60)
    print()

    bus = get_event_bus()

    # Wildcard listener (receives ALL events)
    async def log_all_events(event: Event):
        print(f"📊 [Logger] {event.type.value} from {event.source}")

    # Subscribe to all events by passing None
    bus.subscribe(None, log_all_events)

    # Publish various events
    await bus.publish(Event(type=EventType.AGENT_STARTED, source="agent-1", data={}))

    await bus.publish(Event(type=EventType.CHANNEL_STARTED, source="telegram", data={}))

    await bus.publish(
        Event(type=EventType.GATEWAY_CLIENT_CONNECTED, source="gateway", data={"client_id": "ui-1"})
    )

    print()


async def demo_multiple_subscribers():
    """Demonstrate multiple subscribers for same event"""
    print("=" * 60)
    print("3️⃣ Multiple Subscribers for Same Event")
    print("=" * 60)
    print()

    bus = get_event_bus()

    # Multiple listeners for the same event
    async def save_message(event: Event):
        text = event.data.get("text", "")
        print(f"💾 Saving to database: {text[:30]}...")

    async def display_message(event: Event):
        text = event.data.get("text", "")
        print(f"📺 Displaying on UI: {text[:30]}...")

    async def log_message(event: Event):
        text = event.data.get("text", "")
        print(f"📝 Logging: {text[:30]}...")

    # All three will be called for AGENT_TEXT events
    bus.subscribe(EventType.AGENT_TEXT, save_message)
    bus.subscribe(EventType.AGENT_TEXT, display_message)
    bus.subscribe(EventType.AGENT_TEXT, log_message)

    # Publish event
    await bus.publish(
        Event(
            type=EventType.AGENT_TEXT,
            source="agent-1",
            data={"text": "This message will trigger all three handlers!"},
        )
    )

    print()


async def demo_event_correlation():
    """Demonstrate event correlation with session/channel IDs"""
    print("=" * 60)
    print("4️⃣ Event Correlation (Session & Channel Tracking)")
    print("=" * 60)
    print()

    bus = get_event_bus()

    # Listener that tracks sessions
    sessions = {}

    async def track_session(event: Event):
        if event.session_id:
            if event.session_id not in sessions:
                sessions[event.session_id] = []
            sessions[event.session_id].append(event.type.value)
            print(f"📊 Session {event.session_id}: {len(sessions[event.session_id])} events")

    bus.subscribe(None, track_session)

    # Publish events with correlation IDs
    session_id = "session-123"

    await bus.publish(
        Event(
            type=EventType.SESSION_CREATED, source="session-manager", session_id=session_id, data={}
        )
    )

    await bus.publish(
        Event(
            type=EventType.AGENT_TEXT,
            source="agent-1",
            session_id=session_id,
            channel_id="telegram",
            data={"text": "Hello!"},
        )
    )

    await bus.publish(
        Event(type=EventType.AGENT_TURN_COMPLETE, source="agent-1", session_id=session_id, data={})
    )

    print()
    print(f"Total events in session: {sessions}")
    print()


async def demo_error_handling():
    """Demonstrate error handling in listeners"""
    print("=" * 60)
    print("5️⃣ Error Handling (Listeners Don't Crash the Bus)")
    print("=" * 60)
    print()

    bus = get_event_bus()

    # Listener that raises an error
    async def buggy_listener(event: Event):
        print("🐛 Buggy listener called")
        raise Exception("Oops! Something went wrong!")

    # Healthy listener
    async def healthy_listener(event: Event):
        print("✅ Healthy listener called (still works!)")

    bus.subscribe(EventType.AGENT_TEXT, buggy_listener)
    bus.subscribe(EventType.AGENT_TEXT, healthy_listener)

    # Publish event - buggy listener will error but healthy one continues
    await bus.publish(
        Event(type=EventType.AGENT_TEXT, source="agent-1", data={"text": "Testing error handling"})
    )

    print()


async def demo_bus_stats():
    """Demonstrate event bus statistics"""
    print("=" * 60)
    print("6️⃣ Event Bus Statistics")
    print("=" * 60)
    print()

    bus = get_event_bus()
    stats = bus.get_stats()

    print(f"EventBus Name: {stats['name']}")
    print(f"Total Events Published: {stats['event_count']}")
    print(f"Total Errors: {stats['error_count']}")
    print(f"Event Types Subscribed: {stats['event_types']}")
    print(f"Total Listeners: {stats['total_listeners']}")
    print(f"Wildcard Listeners: {stats['wildcard_listeners']}")
    print()


async def demo_custom_bus():
    """Demonstrate creating a custom event bus"""
    print("=" * 60)
    print("7️⃣ Custom Event Bus (Isolated from Global)")
    print("=" * 60)
    print()

    # Create a custom bus (separate from global)
    custom_bus = EventBus(name="custom-agent-bus")

    async def custom_listener(event: Event):
        print(f"🎯 Custom bus received: {event.type.value}")

    custom_bus.subscribe(EventType.AGENT_TEXT, custom_listener)

    # This only goes to custom bus
    await custom_bus.publish(
        Event(
            type=EventType.AGENT_TEXT,
            source="custom-agent",
            data={"text": "This is in the custom bus"},
        )
    )

    print(f"Custom bus stats: {custom_bus.get_stats()}")
    print(f"Global bus stats: {get_event_bus().get_stats()}")
    print()


async def main():
    """Run all demos"""
    setup_logging(level="INFO", format_type="colored")

    print()
    print("🦞 OpenClaw - Unified Event System Demo")
    print()

    # Reset global bus for clean demo
    from openclaw.events import reset_event_bus

    reset_event_bus()

    await demo_basic_events()
    await demo_wildcard_subscription()
    await demo_multiple_subscribers()
    await demo_event_correlation()
    await demo_error_handling()
    await demo_bus_stats()
    await demo_custom_bus()

    print("=" * 60)
    print("✅ All demos completed!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. Integrate EventBus into AgentRuntime")
    print("2. Integrate EventBus into ChannelManager")
    print("3. Integrate EventBus into GatewayServer")
    print("4. Replace old event systems")
    print()


if __name__ == "__main__":
    asyncio.run(main())
