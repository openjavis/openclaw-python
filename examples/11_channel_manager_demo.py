"""
Example 11: ChannelManager Demo

This example demonstrates how to use ChannelManager independently,
showing all its features for managing channel plugins.

ChannelManager Features:
- Register channel classes or instances
- Configure channels per-channel settings
- Start/stop individual channels
- Set custom AgentRuntime per channel
- Event system for lifecycle notifications

Usage:
    uv run python examples/11_channel_manager_demo.py
"""

import asyncio
import logging
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import SessionManager
from openclaw.channels.enhanced_telegram import EnhancedTelegramChannel
from openclaw.gateway import (
    ChannelManager,
    ChannelState,
    discover_channel_plugins,
)
from openclaw.monitoring import setup_logging

logger = logging.getLogger(__name__)


async def demo_channel_manager():
    """Demonstrate ChannelManager features"""

    print("🦞 ChannelManager Demo")
    print("=" * 60)
    print()

    # =========================================================================
    # 1. Create Core Components
    # =========================================================================

    print("1️⃣ Creating core components...")

    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    session_manager = SessionManager(workspace)
    agent_runtime = AgentRuntime(
        model="anthropic/claude-sonnet-4-20250514",
        enable_context_management=True,
    )

    # =========================================================================
    # 2. Create ChannelManager
    # =========================================================================

    print("2️⃣ Creating ChannelManager...")

    channel_manager = ChannelManager(
        default_runtime=agent_runtime,
        session_manager=session_manager,
    )

    # =========================================================================
    # 3. Discover Available Plugins
    # =========================================================================

    print("3️⃣ Discovering channel plugins...")

    available_plugins = discover_channel_plugins()
    print(f"   Found {len(available_plugins)} plugins:")
    for plugin_id in available_plugins:
        print(f"      - {plugin_id}")
    print()

    # =========================================================================
    # 4. Register Channels
    # =========================================================================

    print("4️⃣ Registering channels...")

    # Method 1: Register class (lazy instantiation)
    channel_manager.register(
        channel_id="telegram",
        channel_class=EnhancedTelegramChannel,
        config={
            "bot_token": "YOUR_BOT_TOKEN",  # Replace with actual token
        },
    )
    print("   ✅ Registered 'telegram' channel class")

    # Method 2: Register instance
    # telegram_instance = EnhancedTelegramChannel()
    # channel_manager.register_instance(telegram_instance, config={...})

    # =========================================================================
    # 5. Configure Channels
    # =========================================================================

    print("5️⃣ Configuring channels...")

    # Configure specific settings
    channel_manager.configure(
        "telegram",
        {
            "parse_mode": "Markdown",
            "enabled": False,  # Disabled for demo (no actual token)
        },
    )
    print("   ✅ Configured 'telegram' channel")

    # =========================================================================
    # 6. Add Event Listener
    # =========================================================================

    print("6️⃣ Adding event listener...")

    async def on_channel_event(event_type: str, channel_id: str, data: dict):
        print(f"   📢 Event: {event_type} for {channel_id}")

    channel_manager.add_event_listener(on_channel_event)
    print("   ✅ Event listener added")

    # =========================================================================
    # 7. Query Channel Status
    # =========================================================================

    print("7️⃣ Querying channel status...")

    all_channels = channel_manager.list_channels()
    print(f"   All channels: {all_channels}")

    enabled_channels = channel_manager.list_enabled()
    print(f"   Enabled channels: {enabled_channels}")

    # Get detailed status
    status = channel_manager.get_status("telegram")
    if status:
        print("   Telegram status:")
        print(f"      - State: {status.get('state')}")
        print(f"      - Enabled: {status.get('enabled')}")

    # =========================================================================
    # 8. Demonstrate Lifecycle Management
    # =========================================================================

    print("8️⃣ Lifecycle management...")

    # Note: This will fail gracefully since we don't have a real token
    # In production, this would start the Telegram bot

    # Enable channel for demonstration
    channel_manager.configure("telegram", {"enabled": True})

    print("   Would call: await channel_manager.start_channel('telegram')")
    print("   Would call: await channel_manager.stop_channel('telegram')")
    print("   Would call: await channel_manager.restart_channel('telegram')")
    print()

    # =========================================================================
    # 9. Full Status Report
    # =========================================================================

    print("9️⃣ Full status report:")

    full_status = channel_manager.get_all_status()
    print(f"   Running: {full_status['running']}")
    print(f"   Total channels: {full_status['total']}")
    print(f"   Running count: {full_status['running_count']}")
    print(f"   Enabled count: {full_status['enabled_count']}")

    # =========================================================================
    # Done
    # =========================================================================

    print()
    print("=" * 60)
    print("✅ ChannelManager demo complete!")
    print()
    print("Key Takeaways:")
    print("  - ChannelManager is part of Gateway")
    print("  - Channels are plugins managed by ChannelManager")
    print("  - Each channel can have its own config (RuntimeEnv)")
    print("  - Channels call Agent Runtime via function calls")
    print("  - Gateway observes Agent events for broadcasting")
    print()


async def demo_integration_with_gateway():
    """Show how ChannelManager integrates with Gateway"""

    print()
    print("🌐 Gateway + ChannelManager Integration")
    print("=" * 60)
    print()
    print("In production, ChannelManager is created inside GatewayServer:")
    print()
    print("```python")
    print("from openclaw.gateway import GatewayServer")
    print()
    print("# Gateway automatically creates ChannelManager")
    print("gateway = GatewayServer(config, agent_runtime)")
    print()
    print("# Access ChannelManager via Gateway")
    print("gateway.channel_manager.register('telegram', TelegramChannel)")
    print("gateway.channel_manager.configure('telegram', {'bot_token': ...})")
    print()
    print("# Start Gateway (also starts all channels)")
    print("await gateway.start()")
    print("```")
    print()


async def main():
    """Run demos"""
    setup_logging(level="INFO", format_type="colored")

    await demo_channel_manager()
    await demo_integration_with_gateway()


if __name__ == "__main__":
    asyncio.run(main())
