"""Test refactored components"""

import asyncio
from pathlib import Path

from openclaw.events import Event, EventType, get_event_bus, reset_event_bus
from openclaw.monitoring import setup_logging
from openclaw.runtime_env import RuntimeEnv, RuntimeEnvManager


async def test_events():
    print("Testing Unified Event System...")
    reset_event_bus()
    bus = get_event_bus()

    received = []

    async def handler(event):
        received.append(event.type.value)

    bus.subscribe(EventType.AGENT_TEXT, handler)

    await bus.publish(Event(type=EventType.AGENT_TEXT, source="test", data={"text": "Hello"}))

    assert len(received) == 1
    print(f"  ✓ Event system works! Received: {received}")


async def test_runtime_env():
    print("Testing RuntimeEnv...")

    env = RuntimeEnv(
        env_id="test", model="anthropic/claude-sonnet-4", workspace=Path("./test_workspace")
    )

    assert env.env_id == "test"
    assert env.model == "anthropic/claude-sonnet-4"
    print(f"  ✓ RuntimeEnv created: {env}")

    manager = RuntimeEnvManager()
    manager.create_env("prod", "anthropic/claude-opus-4")
    manager.create_env("dev", "anthropic/claude-haiku")

    assert len(manager.list_envs()) == 2
    print(f"  ✓ RuntimeEnvManager works! Envs: {manager.list_envs()}")


async def main():
    setup_logging(level="INFO", format_type="colored")

    print("\n🦞 Testing Refactored Architecture\n")

    await test_events()
    await test_runtime_env()

    print("\n✅ All tests passed!\n")


if __name__ == "__main__":
    asyncio.run(main())
