"""
Example 1: Basic Agent Usage

This example shows how to:
1. Create an AgentRuntime
2. Create a Session
3. Send messages to the agent
4. Process responses
"""

import asyncio
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import Session


async def main():
    """Run basic agent example"""

    # Create workspace directory
    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    # Create agent runtime
    # Make sure you have ANTHROPIC_API_KEY or OPENAI_API_KEY in environment
    runtime = AgentRuntime(
        model="anthropic/claude-opus-4",  # or "openai/gpt-4o"
        enable_context_management=True,  # Enable automatic context management
    )

    # Create a session
    session = Session("example-session", workspace)

    print("🤖 ClawdBot Agent Example")
    print("=" * 50)
    print("\nSending message to agent...\n")

    # Send a message
    message = "Hello! Can you explain what you are in one sentence?"

    # Process response
    full_response = ""
    async for event in runtime.run_turn(session, message):
        if event.type == "assistant":
            # Handle assistant response
            delta = event.data.get("delta", {})
            if "text" in delta:
                text = delta["text"]
                print(text, end="", flush=True)
                full_response += text

        elif event.type == "tool":
            # Handle tool calls
            tool_name = event.data.get("toolName")
            print(f"\n[Tool: {tool_name}]", flush=True)

    print("\n\n" + "=" * 50)
    print(f"\n✅ Response received ({len(full_response)} characters)")
    print(f"📝 Session has {len(session.messages)} messages")

    # You can continue the conversation
    print("\n\nSending follow-up...\n")

    async for event in runtime.run_turn(session, "What can you help me with?"):
        if event.type == "assistant":
            delta = event.data.get("delta", {})
            if "text" in delta:
                print(delta["text"], end="", flush=True)

    print("\n\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
