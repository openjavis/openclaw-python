"""
Example 2: Agent with Tools

This example shows how to:
1. Load and use tools
2. Configure tool permissions
3. Handle tool calls
"""

import asyncio
from pathlib import Path

from openclaw.agents.tools.read import ReadTool
from openclaw.agents.tools.write import WriteTool

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import Session
from openclaw.agents.tools.base import ToolConfig, ToolPermission
from openclaw.agents.tools.bash import BashTool


async def main():
    """Run agent with tools example"""

    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    # Create runtime
    runtime = AgentRuntime(model="anthropic/claude-opus-4")

    # Create session
    session = Session("tools-session", workspace)

    # Create and configure tools
    bash_tool = BashTool()
    bash_tool.configure(
        ToolConfig(
            timeout_seconds=30.0,
            allowed_permissions={ToolPermission.EXECUTE, ToolPermission.READ},
            rate_limit_per_minute=10,
        )
    )

    read_tool = ReadTool()
    write_tool = WriteTool()

    tools = [bash_tool, read_tool, write_tool]

    print("🔧 ClawdBot Agent with Tools Example")
    print("=" * 50)
    print(f"\nAvailable tools: {', '.join(t.name for t in tools)}")
    print("\nAsking agent to list files...\n")

    # Ask agent to use tools
    message = "List all Python files in the current directory"

    async for event in runtime.run_turn(session, message, tools=tools):
        if event.type == "assistant":
            delta = event.data.get("delta", {})
            if "text" in delta:
                print(delta["text"], end="", flush=True)

        elif event.type == "tool":
            # Tool being called
            tool_name = event.data.get("toolName")
            print(f"\n\n[🔧 Tool: {tool_name}]")

        elif event.type == "toolResult":
            # Tool result
            result = event.data.get("result", {})
            if result.get("success"):
                print("[✅ Tool succeeded]")
            else:
                print(f"[❌ Tool failed: {result.get('error')}]")

    print("\n\n" + "=" * 50)

    # Show tool metrics
    print("\n📊 Tool Metrics:\n")
    for tool in tools:
        metrics = tool.metrics
        if metrics.total_calls > 0:
            print(f"{tool.name}:")
            print(f"  Total calls: {metrics.total_calls}")
            print(f"  Success rate: {metrics.success_rate:.1%}")
            print(f"  Avg time: {metrics.avg_execution_time_ms:.1f}ms")

    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
