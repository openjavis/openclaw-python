"""
Example: Phoenix (Arize AI) Integration for LLM Observability

This example shows how to integrate Phoenix for advanced LLM monitoring:
- Automatic LLM call tracing
- Token usage tracking
- Cost analysis
- Latency monitoring
- Prompt/response logging

Prerequisites:
    pip install arize-phoenix opentelemetry-api opentelemetry-sdk
"""

import asyncio
import os
from pathlib import Path

# Check if Phoenix is available
try:
    import phoenix as px
    from phoenix.trace import using_project
    from phoenix.otel import register
    PHOENIX_AVAILABLE = True
except ImportError:
    print("❌ Phoenix not installed. Install with: pip install arize-phoenix")
    PHOENIX_AVAILABLE = False

from openclaw.agents.runtime import MultiProviderRuntime
from openclaw.agents.session import SessionManager
from openclaw.monitoring import setup_logging


async def main():
    """Run Phoenix monitoring example"""
    
    if not PHOENIX_AVAILABLE:
        print("\n⚠️  This example requires Phoenix (Arize AI)")
        print("Install with: pip install arize-phoenix")
        print("\nAlternatively, use OpenTelemetry integration:")
        print("  pip install opentelemetry-api opentelemetry-sdk")
        print("  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318")
        return
    
    # Setup logging
    setup_logging(level="INFO", format_type="colored")
    
    print("🔍 Phoenix (Arize AI) LLM Observability Example")
    print("=" * 60)
    
    # =========================================================================
    # Option 1: Launch Phoenix Locally
    # =========================================================================
    print("\n📊 Starting Phoenix server...")
    
    # Launch Phoenix app (opens at http://localhost:6006)
    session = px.launch_app()
    
    print(f"✅ Phoenix running at: {session.url}")
    print(f"   Dashboard: {session.url}")
    
    # =========================================================================
    # Option 2: Register OpenTelemetry with Phoenix
    # =========================================================================
    print("\n🔧 Configuring OpenTelemetry...")
    
    # Register Phoenix as OpenTelemetry backend
    tracer_provider = register(
        project_name="openclaw-example",
        endpoint=f"{session.url}/v1/traces"
    )
    
    print("✅ OpenTelemetry configured to export to Phoenix")
    
    # =========================================================================
    # Option 3: Use Phoenix Context
    # =========================================================================
    print("\n🤖 Running agent with Phoenix tracing...")
    
    with using_project("openclaw-example"):
        # Create workspace
        workspace = Path("./workspace")
        workspace.mkdir(exist_ok=True)
        
        # Initialize runtime and session
        runtime = MultiProviderRuntime()
        session_manager = SessionManager(workspace_dir=workspace)
        
        session = session_manager.get_or_create("phoenix-test")
        
        # Run agent turns (Phoenix auto-captures everything)
        test_messages = [
            "Hello! What's 2+2?",
            "What's the capital of France?",
            "Write a haiku about coding",
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📝 Request {i}/{len(test_messages)}: {message}")
            
            response_text = ""
            async for event in runtime.run_turn(session, message):
                if event.type == "text":
                    text = event.data.get("text", "")
                    response_text += text
                    print(text, end="", flush=True)
            
            print("\n")
            
            # Small delay between requests
            await asyncio.sleep(1)
    
    # =========================================================================
    # View Results
    # =========================================================================
    print("\n" + "=" * 60)
    print("✅ Example Complete!")
    print("\n📊 View detailed traces in Phoenix:")
    print(f"   {session.url}")
    print("\nPhoenix shows:")
    print("  • 📈 Token usage per request")
    print("  • 💰 Cost breakdown")
    print("  • ⏱️  Latency analysis")
    print("  • 🔍 Full prompt/response pairs")
    print("  • 📊 Span visualization")
    print("\nPress Ctrl+C to stop Phoenix server...")
    
    # Keep Phoenix server running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Phoenix...")


async def example_with_manual_logging():
    """Example: Manual logging to Phoenix (without auto-instrumentation)"""
    
    if not PHOENIX_AVAILABLE:
        return
    
    print("\n🔍 Manual Phoenix Logging Example")
    print("=" * 60)
    
    # Launch Phoenix
    session = px.launch_app()
    
    # Manual span creation
    from opentelemetry import trace
    
    tracer = trace.get_tracer("openclaw-manual")
    
    with tracer.start_as_current_span("agent_turn") as span:
        span.set_attribute("message", "Hello, world!")
        span.set_attribute("model", "gemini-3-pro-preview")
        
        # Simulate LLM call
        with tracer.start_as_current_span("llm_call") as llm_span:
            llm_span.set_attribute("input_tokens", 10)
            llm_span.set_attribute("output_tokens", 20)
            llm_span.set_attribute("cost_usd", 0.0001)
            
            await asyncio.sleep(0.5)  # Simulate latency
        
        span.set_attribute("response", "Hello! How can I help?")
    
    print(f"✅ Manual span logged to Phoenix: {session.url}")


async def example_with_phoenix_cloud():
    """Example: Export to Phoenix Cloud (production)"""
    
    if not PHOENIX_AVAILABLE:
        return
    
    print("\n☁️  Phoenix Cloud Integration Example")
    print("=" * 60)
    
    # For Phoenix Cloud, set these environment variables:
    # export PHOENIX_API_KEY=your_api_key
    # export PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com
    
    api_key = os.environ.get("PHOENIX_API_KEY")
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com")
    
    if not api_key:
        print("⚠️  PHOENIX_API_KEY not set")
        print("\nTo use Phoenix Cloud:")
        print("  1. Sign up at https://app.phoenix.arize.com")
        print("  2. Get your API key")
        print("  3. export PHOENIX_API_KEY=your_key")
        print("  4. export PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com")
        return
    
    # Register with Phoenix Cloud
    tracer_provider = register(
        project_name="openclaw-production",
        endpoint=f"{endpoint}/v1/traces"
    )
    
    print(f"✅ Configured to export to Phoenix Cloud")
    print(f"   Endpoint: {endpoint}")
    print(f"   Project: openclaw-production")
    
    # Your bot runs normally, traces go to cloud
    runtime = MultiProviderRuntime()
    session_manager = SessionManager()
    
    session = session_manager.get_or_create("cloud-user")
    
    async for event in runtime.run_turn(session, "Test message"):
        if event.type == "text":
            print(event.data.get("text"), end="")
    
    print(f"\n✅ Trace sent to Phoenix Cloud: {endpoint}")


if __name__ == "__main__":
    # Run main example
    asyncio.run(main())
    
    # Uncomment to try other examples:
    # asyncio.run(example_with_manual_logging())
    # asyncio.run(example_with_phoenix_cloud())
