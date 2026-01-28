"""
Example: Advanced Features Demo

This example demonstrates all the advanced features in ClawdBot:
- Thinking Mode (stream/on/off)
- Auth Profile Rotation
- Model Fallback Chains
- Session Queuing
- Advanced Context Compaction
- Tool Result Formatting
"""

import asyncio
import os
from pathlib import Path

from clawdbot.agents.auth import AuthProfile
from clawdbot.agents.compaction import CompactionStrategy
from clawdbot.agents.formatting import FormatMode
from clawdbot.agents.runtime import AgentRuntime
from clawdbot.agents.session import Session
from clawdbot.agents.thinking import ThinkingMode


async def demo_thinking_mode():
    """Demo 1: Thinking Mode - See AI reasoning process"""
    print("\n" + "=" * 60)
    print("DEMO 1: Thinking Mode")
    print("=" * 60 + "\n")

    # Create runtime with thinking mode enabled
    runtime = AgentRuntime(
        model="anthropic/claude-sonnet-4-5",
        thinking_mode=ThinkingMode.STREAM,  # Stream thinking separately
        enable_queuing=False,
    )

    session = Session("thinking-demo", Path("./workspace"))

    message = "What is 15 * 24? Think step by step."
    print(f"User: {message}\n")

    print("Assistant (with thinking):")
    print("-" * 40)

    async for event in runtime.run_turn(session, message, max_tokens=500):
        if event.type == "thinking":
            # Thinking is streamed separately
            print(
                f"💭 [Thinking]: {event.data.get('delta', {}).get('text', '')}", end="", flush=True
            )
        elif event.type == "assistant":
            # Regular response
            delta = event.data.get("delta", {})
            if "text" in delta:
                print(delta["text"], end="", flush=True)

    print("\n")


async def demo_auth_rotation():
    """Demo 2: Auth Profile Rotation - Multiple API keys with failover"""
    print("\n" + "=" * 60)
    print("DEMO 2: Auth Profile Rotation")
    print("=" * 60 + "\n")

    # Setup multiple auth profiles
    profiles = []

    if os.getenv("ANTHROPIC_API_KEY"):
        profiles.append(
            AuthProfile(
                id="anthropic-main", provider="anthropic", api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        )

    if os.getenv("ANTHROPIC_API_KEY_2"):
        profiles.append(
            AuthProfile(
                id="anthropic-backup",
                provider="anthropic",
                api_key=os.getenv("ANTHROPIC_API_KEY_2"),
            )
        )

    if not profiles:
        print("⚠️  Skipping: No auth profiles configured")
        print("Set ANTHROPIC_API_KEY or ANTHROPIC_API_KEY_2 to test")
        return

    AgentRuntime(model="anthropic/claude-sonnet-4-5", auth_profiles=profiles)

    print(f"✅ Configured {len(profiles)} auth profile(s)")
    print("If one fails, runtime will automatically rotate to the next")


async def demo_model_fallback():
    """Demo 3: Model Fallback Chains - Automatic model switching"""
    print("\n" + "=" * 60)
    print("DEMO 3: Model Fallback Chains")
    print("=" * 60 + "\n")

    # Configure fallback chain
    AgentRuntime(
        model="anthropic/claude-opus-4-5",
        fallback_models=["anthropic/claude-sonnet-4-5", "openai/gpt-4"],
    )

    print("Fallback Chain:")
    print("  1. Primary: anthropic/claude-opus-4-5")
    print("  2. Fallback 1: anthropic/claude-sonnet-4-5")
    print("  3. Fallback 2: openai/gpt-4")
    print()
    print("If primary fails, automatically tries fallbacks!")


async def demo_session_queuing():
    """Demo 4: Session Queuing - Prevent concurrent session access"""
    print("\n" + "=" * 60)
    print("DEMO 4: Session Queuing")
    print("=" * 60 + "\n")

    AgentRuntime(model="anthropic/claude-sonnet-4-5", enable_queuing=True)  # Enable queuing

    print("✅ Queuing enabled")
    print("- Per-session: Sequential (no conflicts)")
    print("- Global: Max 10 concurrent requests")
    print()
    print("This prevents race conditions in session state!")


async def demo_context_compaction():
    """Demo 5: Advanced Context Compaction"""
    print("\n" + "=" * 60)
    print("DEMO 5: Advanced Context Compaction")
    print("=" * 60 + "\n")

    # Create runtime with different compaction strategies
    strategies = [
        CompactionStrategy.KEEP_RECENT,
        CompactionStrategy.KEEP_IMPORTANT,
        CompactionStrategy.SLIDING_WINDOW,
    ]

    for strategy in strategies:
        AgentRuntime(
            model="anthropic/claude-sonnet-4-5",
            compaction_strategy=strategy,
            enable_context_management=True,
        )
        print(f"Strategy: {strategy.value}")
        print("  - Intelligently prunes messages when context is full")

    print()
    print("✅ Context compaction will activate automatically!")


async def demo_tool_formatting():
    """Demo 6: Tool Result Formatting"""
    print("\n" + "=" * 60)
    print("DEMO 6: Tool Result Formatting")
    print("=" * 60 + "\n")

    # Markdown format (for rich channels like Telegram/Web)
    AgentRuntime(model="anthropic/claude-sonnet-4-5", tool_format=FormatMode.MARKDOWN)
    print("Markdown Format (for Telegram/Web/Discord):")
    print("  - Rich formatting with code blocks")
    print("  - Syntax highlighting")
    print("  - Icons and structure")

    # Plain format (for SMS/simple channels)
    AgentRuntime(model="anthropic/claude-sonnet-4-5", tool_format=FormatMode.PLAIN)
    print("\nPlain Format (for SMS/simple channels):")
    print("  - Simple text output")
    print("  - No markdown syntax")
    print("  - Compact display")


async def demo_all_together():
    """Demo 7: All Features Combined"""
    print("\n" + "=" * 60)
    print("DEMO 7: All Features Combined")
    print("=" * 60 + "\n")

    # Configure runtime with ALL advanced features
    AgentRuntime(
        model="anthropic/claude-opus-4-5",
        # Thinking mode
        thinking_mode=ThinkingMode.STREAM,
        # Fallback chain
        fallback_models=["anthropic/claude-sonnet-4-5", "openai/gpt-4"],
        # Auth rotation (if profiles configured)
        auth_profiles=(
            [
                AuthProfile(
                    id="main", provider="anthropic", api_key=os.getenv("ANTHROPIC_API_KEY", "")
                )
            ]
            if os.getenv("ANTHROPIC_API_KEY")
            else None
        ),
        # Queuing
        enable_queuing=True,
        # Context management
        enable_context_management=True,
        compaction_strategy=CompactionStrategy.KEEP_IMPORTANT,
        # Tool formatting
        tool_format=FormatMode.MARKDOWN,
        # Retry
        max_retries=3,
    )

    print("✅ Runtime configured with:")
    print("  🧠 Thinking Mode: stream")
    print("  🔄 Fallback Chain: 3 models")
    print("  🔑 Auth Rotation: enabled")
    print("  📊 Session Queuing: enabled")
    print("  🗜️  Advanced Compaction: keep_important")
    print("  📝 Tool Format: markdown")
    print()
    print("All features work together seamlessly!")


async def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("CLAWDBOT ADVANCED FEATURES DEMO")
    print("=" * 60)

    demos = [
        ("Thinking Mode", demo_thinking_mode),
        ("Auth Profile Rotation", demo_auth_rotation),
        ("Model Fallback Chains", demo_model_fallback),
        ("Session Queuing", demo_session_queuing),
        ("Context Compaction", demo_context_compaction),
        ("Tool Formatting", demo_tool_formatting),
        ("All Together", demo_all_together),
    ]

    for i, (name, demo_fn) in enumerate(demos, 1):
        try:
            await demo_fn()
        except Exception as e:
            print(f"\n❌ {name} error: {e}")

        if i < len(demos):
            await asyncio.sleep(0.5)

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print()
    print("Summary of Advanced Features:")
    print("✅ Thinking Mode - Extract and display AI reasoning")
    print("✅ Auth Rotation - Multiple API keys with auto-failover")
    print("✅ Model Fallback - Automatic backup model switching")
    print("✅ Session Queuing - Prevent concurrent conflicts")
    print("✅ Context Compaction - Intelligent message pruning")
    print("✅ Tool Formatting - Channel-appropriate output")
    print()
    print("These features bring Python implementation to parity")
    print("with TypeScript pi-agent capabilities!")


if __name__ == "__main__":
    asyncio.run(main())
