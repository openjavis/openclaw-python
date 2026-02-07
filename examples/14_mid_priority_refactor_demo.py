"""
Example 14: Mid-Priority Refactoring Demo

Demonstrates the mid-priority refactoring improvements:
1. Unified Configuration System (OpenClawConfig)
2. Gateway API Standardization (MethodRegistry)

Usage:
    uv run python examples/14_mid_priority_refactor_demo.py
"""

import asyncio
import logging
from pathlib import Path

from openclaw.config.unified import ConfigBuilder, OpenClawConfig, load_config
from openclaw.gateway.api import MethodRegistry, get_method_registry
from openclaw.monitoring import setup_logging

logger = logging.getLogger(__name__)


# =============================================================================
# Demo 1: Unified Configuration System
# =============================================================================


async def demo_unified_config():
    """Demonstrate unified configuration system"""
    print("=" * 60)
    print("1️⃣  Unified Configuration System (OpenClawConfig)")
    print("=" * 60)
    print()

    # Method 1: Direct instantiation
    print("Method 1: Direct instantiation")
    config1 = OpenClawConfig(
        agent={"model": "anthropic/claude-sonnet-4", "workspace": "~/.openclaw/workspace"},
        gateway={"port": 8765, "auto_start_channels": True},
    )
    print(
        f"  ✓ Created config: agent.model={config1.agent.model.model if hasattr(config1.agent.model, 'model') else config1.agent.model}"
    )
    print()

    # Method 2: Builder pattern
    print("Method 2: Builder pattern (fluent API)")
    config2 = (
        ConfigBuilder()
        .with_agent(model="anthropic/claude-opus-4", temperature=0.7)
        .with_gateway(port=8765, auto_start_channels=True)
        .with_channel("telegram", enabled=True, config={"bot_token": "test"})
        .with_monitoring(log_level="INFO", metrics_enabled=True)
        .build()
    )
    print(f"  ✓ Built config with {len(list(config2.channels))} channels")
    print()

    # Method 3: From dict
    print("Method 3: From dictionary")
    config3 = OpenClawConfig.from_dict(
        {"agent": {"model": "anthropic/claude-haiku"}, "gateway": {"port": 9000}}
    )
    print(f"  ✓ Loaded from dict: gateway.port={config3.gateway.port}")
    print()

    # Method 4: Load from environment/file
    print("Method 4: Smart loading (load_config)")
    config4 = load_config()  # Tries env, files, then defaults
    print(f"  ✓ Loaded config: version={config4.version}")
    print()

    # Configuration features
    print("Configuration features:")
    print("  - Type-safe validation: ✓")
    print("  - Nested configuration: ✓")
    print("  - Default values: ✓")
    print("  - JSON/YAML support: ✓")
    print("  - Environment variables: ✓")
    print()


# =============================================================================
# Demo 2: Gateway API Method Registry
# =============================================================================


async def demo_method_registry():
    """Demonstrate Gateway API method registry"""
    print("=" * 60)
    print("2️⃣  Gateway API Method Registry")
    print("=" * 60)
    print()

    # Get global registry
    registry = get_method_registry()

    print(f"Total methods: {registry.get_method_count()}")
    print()

    # List by category
    print("Methods by category:")
    for category in registry.get_categories():
        methods = registry.list_by_category(category)
        print(f"  {category}: {len(methods)} methods")
        for method_name in methods:
            method = registry.get(method_name)
            print(f"    - {method_name}: {method.description}")
    print()

    # Test method execution
    print("Testing method execution:")

    # Create mock connection
    class MockConnection:
        def __init__(self):
            self.client_info = None
            self.protocol_version = 0
            self.authenticated = False

    connection = MockConnection()

    # Test connect method
    connect_method = registry.get("connect")
    if connect_method:
        result = await connect_method.execute(
            connection,
            {
                "maxProtocol": 1,
                "client": {"name": "test-client", "version": "1.0.0", "platform": "python"},
            },
        )
        print(f"  ✓ connect: {result['server']['name']} v{result['server']['version']}")

    # Test ping method
    ping_method = registry.get("ping")
    if ping_method:
        result = await ping_method.execute(connection, {"timestamp": 123456})
        print(f"  ✓ ping: pong={result['pong']}")

    # Test health method
    health_method = registry.get("health")
    if health_method:
        result = await health_method.execute(connection, {})
        print(f"  ✓ health: status={result['status']}")

    print()


# =============================================================================
# Demo 3: API Documentation Generation
# =============================================================================


async def demo_api_docs():
    """Demonstrate API documentation generation"""
    print("=" * 60)
    print("3️⃣  API Documentation Generation")
    print("=" * 60)
    print()

    registry = get_method_registry()
    docs = registry.generate_docs()

    print("API Documentation:")
    print(f"  Total methods: {docs['total_methods']}")
    print()

    print("Categories:")
    for category, info in docs["categories"].items():
        print(f"  {category}: {info['count']} methods")
    print()

    print("Sample method documentation:")
    agent_method = docs["methods"].get("agent")
    if agent_method:
        print(f"  Method: {agent_method['name']}")
        print(f"  Description: {agent_method['description']}")
        print(f"  Category: {agent_method['category']}")
        print(f"  Schema: {agent_method['schema'].get('type', 'N/A')}")
    print()


# =============================================================================
# Demo 4: Configuration + API Integration
# =============================================================================


async def demo_integration():
    """Demonstrate configuration and API working together"""
    print("=" * 60)
    print("4️⃣  Configuration + API Integration")
    print("=" * 60)
    print()

    # Create config
    config = (
        ConfigBuilder()
        .with_agent(model="anthropic/claude-sonnet-4")
        .with_gateway(port=8765, auto_start_channels=True)
        .with_channel("telegram", enabled=True)
        .with_channel("discord", enabled=False)
        .build()
    )

    print("Configuration:")
    print(f"  Gateway port: {config.gateway.port}")
    print(f"  Auto-start channels: {config.gateway.auto_start_channels}")
    print()

    # Get enabled channels
    enabled = config.get_enabled_channels()
    print(f"Enabled channels: {list(enabled.keys())}")
    print()

    # Show how Gateway would use this
    registry = get_method_registry()
    print(f"Gateway API methods available: {registry.get_method_count()}")
    print()

    print("Integration complete:")
    print("  ✓ Configuration defines server settings")
    print("  ✓ API methods handle client requests")
    print("  ✓ Channels configured via config")
    print("  ✓ Type-safe end-to-end")
    print()


# =============================================================================
# Main Demo
# =============================================================================


async def main():
    """Run all demos"""
    setup_logging(level="INFO", format_type="colored")

    print()
    print("🦞 OpenClaw - Mid-Priority Refactoring Demo")
    print()
    print("This demo showcases:")
    print("✨ Unified Configuration System (OpenClawConfig)")
    print("✨ Gateway API Standardization (MethodRegistry)")
    print("✨ Auto-generated API Documentation")
    print()

    await demo_unified_config()
    await demo_method_registry()
    await demo_api_docs()
    await demo_integration()

    print("=" * 60)
    print("✅ All mid-priority refactoring demos completed!")
    print("=" * 60)
    print()
    print("Improvements:")
    print("  1. Type-safe configuration with validation")
    print("  2. Standardized Gateway API (8+ methods)")
    print("  3. Auto-generated documentation")
    print("  4. Fluent configuration builder")
    print()
    print("Next: Testing and channel lifecycle updates")
    print()


if __name__ == "__main__":
    asyncio.run(main())
