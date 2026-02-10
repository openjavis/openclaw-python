"""Tests for health check system (matches TypeScript test patterns)"""

import asyncio
import pytest
from openclaw.monitoring.health import (
    HealthCheck,
    HealthStatus,
    ComponentHealth,
)


@pytest.mark.asyncio
async def test_health_check_initialization():
    """Test HealthCheck initialization"""
    health = HealthCheck()
    assert health is not None
    assert len(health.components) == 0


@pytest.mark.asyncio
async def test_register_component():
    """Test component registration"""
    health = HealthCheck()
    
    async def check_fn():
        return ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            message="OK",
        )
    
    health.register("test", check_fn)
    assert "test" in health.components


@pytest.mark.asyncio
async def test_check_component_healthy():
    """Test healthy component check"""
    health = HealthCheck()
    
    async def check_fn():
        return ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All systems operational",
        )
    
    health.register("test", check_fn)
    result = await health.check_component("test")
    
    assert result.name == "test"
    assert result.status == HealthStatus.HEALTHY
    assert result.message == "All systems operational"


@pytest.mark.asyncio
async def test_check_component_unhealthy():
    """Test unhealthy component check"""
    health = HealthCheck()
    
    async def check_fn():
        return ComponentHealth(
            name="test",
            status=HealthStatus.UNHEALTHY,
            message="Service down",
        )
    
    health.register("test", check_fn)
    result = await health.check_component("test")
    
    assert result.status == HealthStatus.UNHEALTHY
    assert result.message == "Service down"


@pytest.mark.asyncio
async def test_check_component_timeout():
    """Test component check timeout"""
    health = HealthCheck()
    
    async def slow_check():
        await asyncio.sleep(10)  # Longer than default timeout
        return ComponentHealth(name="slow", status=HealthStatus.HEALTHY)
    
    health.register("slow", slow_check, timeout_sec=0.1)
    result = await health.check_component("slow")
    
    assert result.status == HealthStatus.UNHEALTHY
    assert "timeout" in result.message.lower()


@pytest.mark.asyncio
async def test_check_component_error():
    """Test component check with error"""
    health = HealthCheck()
    
    async def error_check():
        raise ValueError("Simulated error")
    
    health.register("error", error_check)
    result = await health.check_component("error")
    
    assert result.status == HealthStatus.UNHEALTHY
    assert "error" in result.message.lower()


@pytest.mark.asyncio
async def test_check_all_components():
    """Test checking all components"""
    health = HealthCheck()
    
    async def healthy_check():
        return ComponentHealth(name="healthy", status=HealthStatus.HEALTHY)
    
    async def degraded_check():
        return ComponentHealth(name="degraded", status=HealthStatus.DEGRADED)
    
    health.register("healthy", healthy_check)
    health.register("degraded", degraded_check)
    
    results = await health.check_all()
    
    assert len(results) == 2
    assert results["healthy"].status == HealthStatus.HEALTHY
    assert results["degraded"].status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_overall_health_all_healthy():
    """Test overall health when all components healthy"""
    health = HealthCheck()
    
    async def check1():
        return ComponentHealth(name="c1", status=HealthStatus.HEALTHY)
    
    async def check2():
        return ComponentHealth(name="c2", status=HealthStatus.HEALTHY)
    
    health.register("c1", check1)
    health.register("c2", check2)
    
    response = await health.get_health()
    
    assert response.status == HealthStatus.HEALTHY
    assert len(response.components) == 2


@pytest.mark.asyncio
async def test_overall_health_degraded():
    """Test overall health when one component degraded"""
    health = HealthCheck()
    
    async def healthy():
        return ComponentHealth(name="h", status=HealthStatus.HEALTHY)
    
    async def degraded():
        return ComponentHealth(name="d", status=HealthStatus.DEGRADED)
    
    health.register("h", healthy)
    health.register("d", degraded)
    
    response = await health.get_health()
    
    assert response.status == HealthStatus.DEGRADED


@pytest.mark.asyncio
async def test_overall_health_unhealthy():
    """Test overall health when critical component unhealthy"""
    health = HealthCheck()
    
    async def healthy():
        return ComponentHealth(name="h", status=HealthStatus.HEALTHY)
    
    async def unhealthy():
        return ComponentHealth(name="u", status=HealthStatus.UNHEALTHY)
    
    health.register("h", healthy, critical=False)
    health.register("u", unhealthy, critical=True)
    
    response = await health.get_health()
    
    assert response.status == HealthStatus.UNHEALTHY


@pytest.mark.asyncio
async def test_liveness_probe():
    """Test liveness probe (always healthy if service running)"""
    health = HealthCheck()
    
    is_alive = await health.liveness()
    assert is_alive is True


@pytest.mark.asyncio
async def test_readiness_probe():
    """Test readiness probe (healthy only if critical components OK)"""
    health = HealthCheck()
    
    async def critical_healthy():
        return ComponentHealth(name="db", status=HealthStatus.HEALTHY)
    
    health.register("db", critical_healthy, critical=True)
    
    is_ready = await health.readiness()
    assert is_ready is True
    
    # Now make it unhealthy
    async def critical_unhealthy():
        return ComponentHealth(name="db", status=HealthStatus.UNHEALTHY)
    
    health.register("db", critical_unhealthy, critical=True)
    
    is_ready = await health.readiness()
    assert is_ready is False


@pytest.mark.asyncio
async def test_component_response_time():
    """Test component response time tracking"""
    health = HealthCheck()
    
    async def check():
        await asyncio.sleep(0.01)  # 10ms
        return ComponentHealth(name="timed", status=HealthStatus.HEALTHY)
    
    health.register("timed", check)
    result = await health.check_component("timed")
    
    assert result.response_time_ms is not None
    assert result.response_time_ms >= 10
