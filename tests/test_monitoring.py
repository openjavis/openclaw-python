"""
Tests for monitoring system
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from openclaw.monitoring.health import ComponentHealth, HealthCheck, HealthStatus, get_health_check
from openclaw.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    Timer,
    get_metrics,
)


class TestHealthStatus:
    """Test HealthStatus enum"""

    def test_status_values(self):
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestComponentHealth:
    """Test ComponentHealth class"""

    def test_component_creation(self):
        health = ComponentHealth(name="test")
        assert health.name == "test"
        assert health.status == HealthStatus.UNKNOWN

    def test_component_to_dict(self):
        health = ComponentHealth(name="test", status=HealthStatus.HEALTHY, message="OK")
        data = health.to_dict()

        assert data["name"] == "test"
        assert data["status"] == "healthy"
        assert data["message"] == "OK"


class TestHealthCheck:
    """Test HealthCheck class"""

    @pytest.mark.asyncio
    async def test_register_check(self):
        health = HealthCheck()

        async def check():
            return True

        health.register("test", check)

        result = await health.check_all()
        assert result.status == "healthy"
        assert "test" in result.components

    @pytest.mark.asyncio
    async def test_unhealthy_check(self):
        health = HealthCheck()

        async def check():
            return False

        health.register("test", check, critical=True)

        result = await health.check_all()
        assert result.status == "unhealthy"

    @pytest.mark.asyncio
    async def test_degraded_check(self):
        health = HealthCheck()

        async def good_check():
            return True

        async def bad_check():
            return False

        health.register("good", good_check, critical=True)
        health.register("bad", bad_check, critical=False)  # Non-critical

        result = await health.check_all()
        assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_check_timeout(self):
        health = HealthCheck()
        health._check_timeout = 0.1

        async def slow_check():
            await asyncio.sleep(10)
            return True

        health.register("slow", slow_check)

        result = await health.check_all()
        assert result.status == "unhealthy"
        assert "timed out" in result.components["slow"]["message"].lower()

    @pytest.mark.asyncio
    async def test_check_exception(self):
        health = HealthCheck()

        async def error_check():
            raise ValueError("Test error")

        health.register("error", error_check)

        result = await health.check_all()
        assert result.status == "unhealthy"
        assert "Test error" in result.components["error"]["message"]

    @pytest.mark.asyncio
    async def test_liveness(self):
        health = HealthCheck()
        assert await health.liveness() is True

    @pytest.mark.asyncio
    async def test_readiness(self):
        health = HealthCheck()

        async def check():
            return True

        health.register("test", check)

        assert await health.readiness() is True

    def test_uptime(self):
        health = HealthCheck()
        assert health.uptime_seconds > 0


class TestCounter:
    """Test Counter metric"""

    def test_counter_init(self):
        counter = Counter(name="test_counter", description="Test")
        assert counter.value == 0.0

    def test_counter_inc(self):
        counter = Counter(name="test_counter")
        counter.inc()
        assert counter.value == 1.0

        counter.inc(5.0)
        assert counter.value == 6.0

    def test_counter_to_dict(self):
        counter = Counter(name="test", description="desc")
        counter.inc()

        data = counter.to_dict()
        assert data["name"] == "test"
        assert data["type"] == "counter"
        assert data["value"] == 1.0


class TestGauge:
    """Test Gauge metric"""

    def test_gauge_init(self):
        gauge = Gauge(name="test_gauge")
        assert gauge.value == 0.0

    def test_gauge_set(self):
        gauge = Gauge(name="test_gauge")
        gauge.set(10.0)
        assert gauge.value == 10.0

    def test_gauge_inc_dec(self):
        gauge = Gauge(name="test_gauge")
        gauge.inc(5.0)
        assert gauge.value == 5.0

        gauge.dec(2.0)
        assert gauge.value == 3.0


class TestHistogram:
    """Test Histogram metric"""

    def test_histogram_init(self):
        hist = Histogram(name="test_histogram")
        assert hist.count == 0
        assert hist.sum == 0.0

    def test_histogram_observe(self):
        hist = Histogram(name="test_histogram")
        hist.observe(1.0)
        hist.observe(2.0)
        hist.observe(3.0)

        assert hist.count == 3
        assert hist.sum == 6.0
        assert hist.avg == 2.0

    def test_histogram_percentile(self):
        hist = Histogram(name="test_histogram")
        for i in range(100):
            hist.observe(float(i))

        p50 = hist.percentile(50)
        assert 45 <= p50 <= 55

    def test_histogram_to_dict(self):
        hist = Histogram(name="test")
        hist.observe(1.0)

        data = hist.to_dict()
        assert data["count"] == 1
        assert data["sum"] == 1.0
        assert "p50" in data
        assert "p95" in data
        assert "p99" in data


class TestMetricsCollector:
    """Test MetricsCollector class"""

    def test_create_counter(self):
        metrics = MetricsCollector()
        counter = metrics.counter("test_counter", "Test counter")

        assert counter.name == "test_counter"
        counter.inc()
        assert counter.value == 1.0

    def test_create_gauge(self):
        metrics = MetricsCollector()
        gauge = metrics.gauge("test_gauge", "Test gauge")

        gauge.set(42.0)
        assert gauge.value == 42.0

    def test_create_histogram(self):
        metrics = MetricsCollector()
        hist = metrics.histogram("test_hist", "Test histogram")

        hist.observe(1.0)
        assert hist.count == 1

    def test_same_metric_returns_same_instance(self):
        metrics = MetricsCollector()
        counter1 = metrics.counter("test")
        counter2 = metrics.counter("test")

        assert counter1 is counter2

    def test_metrics_with_labels(self):
        metrics = MetricsCollector()
        counter1 = metrics.counter("requests", labels={"method": "GET"})
        counter2 = metrics.counter("requests", labels={"method": "POST"})

        counter1.inc()
        counter2.inc(2)

        assert counter1.value == 1.0
        assert counter2.value == 2.0

    def test_to_dict(self):
        metrics = MetricsCollector()
        metrics.counter("test_counter").inc()
        metrics.gauge("test_gauge").set(10)

        data = metrics.to_dict()

        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "counters" in data
        assert "gauges" in data

    def test_to_prometheus(self):
        metrics = MetricsCollector()
        metrics.counter("http_requests", "Total requests").inc()

        prom = metrics.to_prometheus()

        assert "http_requests" in prom
        assert "counter" in prom

    def test_reset(self):
        metrics = MetricsCollector()
        metrics.counter("test").inc()

        metrics.reset()

        assert len(metrics._counters) == 0


class TestTimer:
    """Test Timer context manager"""

    @pytest.mark.asyncio
    async def test_timer_async(self):
        hist = Histogram(name="test")

        async with Timer(hist):
            await asyncio.sleep(0.1)

        assert hist.count == 1
        assert hist.avg >= 0.1

    def test_timer_sync(self):
        hist = Histogram(name="test")

        with Timer(hist):
            import time

            time.sleep(0.1)

        assert hist.count == 1
        assert hist.avg >= 0.1
