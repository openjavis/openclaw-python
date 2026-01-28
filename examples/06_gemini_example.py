"""
Example: Using Google Gemini with ClawdBot

This example demonstrates how to use Google Gemini models with ClawdBot.
"""

import asyncio
import os

from clawdbot.agents.runtime import MultiProviderRuntime
from clawdbot.agents.session import Session


async def main():
    """Run example with Gemini"""

    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Please set GOOGLE_API_KEY environment variable")
        print("Get your API key from: https://makersuite.google.com/app/apikey")
        return

    print("=== ClawdBot with Google Gemini ===\n")

    # Create runtime with Gemini
    runtime = MultiProviderRuntime(
        model="gemini/gemini-pro",  # or gemini-3-pro-preview, gemini-3-flash-preview
        api_key=os.getenv("GOOGLE_API_KEY"),
    )

    # Create session
    session = Session("gemini-demo", "./workspace")

    # Example 1: Simple conversation
    print("📝 Example 1: Simple Question\n")

    message = "What are the main differences between Python and JavaScript? Please be concise."
    print(f"User: {message}\n")
    print("Gemini: ", end="", flush=True)

    async for event in runtime.run_turn(session, message):
        if event.type == "assistant":
            if "delta" in event.data and "text" in event.data["delta"]:
                print(event.data["delta"]["text"], end="", flush=True)

    print("\n\n" + "=" * 60 + "\n")

    # Example 2: Follow-up question
    print("📝 Example 2: Follow-up Question\n")

    follow_up = "Can you give me a code example showing async/await in both languages?"
    print(f"User: {follow_up}\n")
    print("Gemini: ", end="", flush=True)

    async for event in runtime.run_turn(session, follow_up):
        if event.type == "assistant":
            if "delta" in event.data and "text" in event.data["delta"]:
                print(event.data["delta"]["text"], end="", flush=True)

    print("\n\n" + "=" * 60 + "\n")

    # Example 3: Show conversation history
    print("📜 Conversation History:\n")
    for i, msg in enumerate(session.messages, 1):
        role = msg.role.upper()
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        print(f"{i}. {role}: {content}\n")

    print(f"\n✅ Total messages in session: {len(session.messages)}")


if __name__ == "__main__":
    asyncio.run(main())
