"""
Example 3: Monitoring and Health Checks

This example shows how to:
1. Setup health checks
2. Collect metrics
3. Export metrics in different formats
"""

import asyncio
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import Session
from openclaw.monitoring import get_health_check, get_metrics, setup_logging


async def main():
    """Run monitoring example"""

    # Setup logging
    setup_logging(level="INFO", format_type="colored")

    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    print("📊 ClawdBot Monitoring Example")
    print("=" * 50)

    # Get health check instance
    health = get_health_check()

    # Register health checks
    async def runtime_health():
        # Check if runtime can be created
        try:
            AgentRuntime()
            return True
        except Exception:
            return False

    async def session_health():
        # Check if sessions can be created
        try:
            Session("health-test", workspace)
            return True
        except Exception:
            return False

    health.register("runtime", runtime_health, critical=True)
    health.register("sessions", session_health, critical=False)

    # Perform health check
    print("\n🏥 Health Check:\n")
    result = await health.check_all()

    print(f"Overall Status: {result.status}")
    print(f"Uptime: {result.uptime_seconds:.1f}s")
    print("\nComponents:")
    for name, component in result.components.items():
        status_emoji = "✅" if component["status"] == "healthy" else "❌"
        print(f"  {status_emoji} {name}: {component['status']}")
        if component.get("responseTimeMs"):
            print(f"     Response time: {component['responseTimeMs']:.1f}ms")

    # Get metrics instance
    metrics = get_metrics()

    # Create some metrics
    requests_counter = metrics.counter("agent_requests", "Total agent requests")
    metrics.histogram("agent_response_time", "Agent response time")
    active_sessions = metrics.gauge("active_sessions", "Active sessions")

    # Simulate some activity
    print("\n\n📈 Simulating Activity...\n")

    runtime = AgentRuntime()
    session = Session("metrics-test", workspace)
    active_sessions.set(1)

    for i in range(3):
        print(f"Request {i + 1}/3...", end=" ", flush=True)
        requests_counter.inc()

        with metrics.timer("agent_request_time"):
            async for event in runtime.run_turn(session, f"Say hello {i + 1}"):
                if event.type == "assistant":
                    pass  # Process silently

        print("✅")
        await asyncio.sleep(0.5)

    # Show metrics
    print("\n\n📊 Metrics:\n")
    all_metrics = metrics.to_dict()

    print("Counters:")
    for name, counter in all_metrics["counters"].items():
        print(f"  {counter['name']}: {counter['value']}")

    print("\nGauges:")
    for name, gauge in all_metrics["gauges"].items():
        print(f"  {gauge['name']}: {gauge['value']}")

    print("\nHistograms:")
    for name, hist in all_metrics["histograms"].items():
        print(f"  {hist['name']}:")
        print(f"    Count: {hist['count']}")
        print(f"    Avg: {hist['avg']:.3f}s")
        print(f"    P95: {hist['p95']:.3f}s")

    # Export in Prometheus format
    print("\n\n📤 Prometheus Format:\n")
    print(metrics.to_prometheus()[:500] + "...")

    print("\n\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
