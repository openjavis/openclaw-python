"""Integration tests for gateway health endpoints"""

import asyncio
import pytest
from openclaw.gateway.bootstrap import GatewayBootstrap
from openclaw.monitoring.health import HealthCheck, ComponentHealth, HealthStatus


@pytest.mark.asyncio
async def test_gateway_health_check_integration():
    """Test full gateway health check integration"""
    
    # Initialize gateway bootstrap
    bootstrap = GatewayBootstrap()
    
    # Run partial bootstrap (skip actual server start)
    results = await bootstrap.bootstrap()
    
    assert results["steps_completed"] >= 10
    assert bootstrap.config is not None
    
    # Test health check with real components
    health = HealthCheck()
    
    # Register runtime health
    async def check_runtime():
        if bootstrap.runtime:
            return ComponentHealth(
                name="runtime",
                status=HealthStatus.HEALTHY,
                message="Runtime initialized",
            )
        return ComponentHealth(
            name="runtime",
            status=HealthStatus.UNHEALTHY,
            message="Runtime not initialized",
        )
    
    health.register("runtime", check_runtime, critical=True)
    
    # Register session manager health
    async def check_sessions():
        if bootstrap.session_manager:
            session_count = len(bootstrap.session_manager.list_sessions())
            return ComponentHealth(
                name="sessions",
                status=HealthStatus.HEALTHY,
                message=f"{session_count} sessions",
                details={"count": session_count},
            )
        return ComponentHealth(
            name="sessions",
            status=HealthStatus.UNHEALTHY,
            message="Session manager not initialized",
        )
    
    health.register("sessions", check_sessions)
    
    # Register tools health
    async def check_tools():
        if bootstrap.tool_registry:
            tool_count = len(bootstrap.tool_registry.list_tools())
            return ComponentHealth(
                name="tools",
                status=HealthStatus.HEALTHY,
                message=f"{tool_count} tools registered",
                details={"count": tool_count},
            )
        return ComponentHealth(
            name="tools",
            status=HealthStatus.DEGRADED,
            message="Tools not fully initialized",
        )
    
    health.register("tools", check_tools)
    
    # Check overall health
    health_response = await health.get_health()
    
    assert health_response.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    assert len(health_response.components) >= 3
    
    # Verify liveness
    assert await health.liveness() is True
    
    # Cleanup
    await bootstrap.shutdown()


@pytest.mark.asyncio
async def test_health_check_with_failures():
    """Test health check handling of component failures"""
    health = HealthCheck()
    
    # Register a failing component
    async def failing_check():
        raise RuntimeError("Simulated component failure")
    
    health.register("failing", failing_check, critical=True)
    
    # Register a healthy component
    async def healthy_check():
        return ComponentHealth(
            name="healthy",
            status=HealthStatus.HEALTHY,
        )
    
    health.register("healthy", healthy_check)
    
    # Check all
    results = await health.check_all()
    
    # Failing component should be marked unhealthy
    assert results["failing"].status == HealthStatus.UNHEALTHY
    assert "error" in results["failing"].message.lower() or "failed" in results["failing"].message.lower()
    
    # Healthy component should be OK
    assert results["healthy"].status == HealthStatus.HEALTHY
    
    # Overall health should be unhealthy due to critical component
    health_response = await health.get_health()
    assert health_response.status == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_readiness_probe_integration():
    """Test readiness probe with real components"""
    health = HealthCheck()
    
    # Simulate components initializing
    initialized = {"db": False, "cache": False}
    
    async def check_db():
        if initialized["db"]:
            return ComponentHealth(name="db", status=HealthStatus.HEALTHY)
        return ComponentHealth(name="db", status=HealthStatus.UNHEALTHY, message="Not initialized")
    
    async def check_cache():
        if initialized["cache"]:
            return ComponentHealth(name="cache", status=HealthStatus.HEALTHY)
        return ComponentHealth(name="cache", status=HealthStatus.HEALTHY, message="Optional")
    
    health.register("db", check_db, critical=True)
    health.register("cache", check_cache, critical=False)
    
    # Before initialization
    ready = await health.readiness()
    assert ready is False
    
    # Initialize DB
    initialized["db"] = True
    ready = await health.readiness()
    assert ready is True
    
    # Cache failure should not affect readiness (non-critical)
    initialized["cache"] = False
    ready = await health.readiness()
    assert ready is True
