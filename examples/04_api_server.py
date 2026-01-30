"""
Example 4: REST API Server

This example shows how to:
1. Start the REST API server
2. Use health check endpoints
3. Use agent chat endpoints
4. Use metrics endpoints

Run this example, then in another terminal:

# Health check
curl http://localhost:8000/health

# List sessions
curl -H "X-API-Key: your-key" http://localhost:8000/agent/sessions

# Chat with agent
curl -X POST http://localhost:8000/agent/chat \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test",
    "message": "Hello!",
    "model": "anthropic/claude-opus-4"
  }'

# Get metrics
curl http://localhost:8000/metrics
"""

import asyncio
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import SessionManager
from openclaw.api import run_api_server
from openclaw.channels.registry import ChannelRegistry
from openclaw.monitoring import setup_logging


async def main():
    """Run API server example"""

    # Setup logging
    setup_logging(level="INFO", format_type="colored")

    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    # Create components
    runtime = AgentRuntime(model="anthropic/claude-opus-4", enable_context_management=True)

    session_manager = SessionManager(workspace)
    channel_registry = ChannelRegistry()

    print("🚀 Starting ClawdBot API Server")
    print("=" * 50)
    print("\nEndpoints:")
    print("  - http://localhost:8000/          (API info)")
    print("  - http://localhost:8000/docs      (Interactive docs)")
    print("  - http://localhost:8000/health    (Health check)")
    print("  - http://localhost:8000/metrics   (Metrics)")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 50)

    # Run server
    await run_api_server(
        host="0.0.0.0",
        port=8000,
        runtime=runtime,
        session_manager=session_manager,
        channel_registry=channel_registry,
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")
