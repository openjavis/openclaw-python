"""
Health check system for ClawdBot
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component"""

    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str | None = None
    last_check: datetime | None = None
    response_time_ms: float | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "lastCheck": self.last_check.isoformat() if self.last_check else None,
            "responseTimeMs": self.response_time_ms,
            "details": self.details,
        }


class HealthCheckResponse(BaseModel):
    """Health check API response"""

    status: str
    timestamp: str
    version: str = "0.3.1"
    uptime_seconds: float | None = None
    components: dict[str, dict] = {}

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class HealthCheck:
    """
    Centralized health check system

    Example usage:
        health = HealthCheck()

        # Register component checks
        health.register("database", db_check_func)
        health.register("redis", redis_check_func)
        health.register("agent", agent_check_func)

        # Get overall health
        result = await health.check_all()
        print(result.status)  # "healthy", "degraded", or "unhealthy"

        # Add to FastAPI
        @app.get("/health")
        async def health_endpoint():
            return await health.check_all()
    """

    def __init__(self):
        self._checks: dict[str, Callable[[], Awaitable[ComponentHealth]]] = {}
        self._start_time = datetime.now(UTC)
        self._last_results: dict[str, ComponentHealth] = {}
        self._check_timeout = 10.0  # seconds

    @property
    def uptime_seconds(self) -> float:
        """Get system uptime in seconds"""
        return (datetime.now(UTC) - self._start_time).total_seconds()

    def register(
        self, name: str, check_fn: Callable[[], Awaitable[bool]], critical: bool = True
    ) -> None:
        """
        Register a health check

        Args:
            name: Component name
            check_fn: Async function that returns True if healthy
            critical: If True, unhealthy status affects overall health
        """

        async def wrapper() -> ComponentHealth:
            start = datetime.now(UTC)
            try:
                result = await asyncio.wait_for(check_fn(), timeout=self._check_timeout)
                elapsed = (datetime.now(UTC) - start).total_seconds() * 1000

                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    message="OK" if result else "Check failed",
                    last_check=datetime.now(UTC),
                    response_time_ms=elapsed,
                    details={"critical": critical},
                )
            except TimeoutError:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message="Check timed out",
                    last_check=datetime.now(UTC),
                    details={"critical": critical, "error": "timeout"},
                )
            except Exception as e:
                elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    last_check=datetime.now(UTC),
                    response_time_ms=elapsed,
                    details={"critical": critical, "error": type(e).__name__},
                )

        self._checks[name] = wrapper
        logger.info(f"Registered health check: {name} (critical={critical})")

    def unregister(self, name: str) -> None:
        """Unregister a health check"""
        if name in self._checks:
            del self._checks[name]
            logger.info(f"Unregistered health check: {name}")

    async def check_component(self, name: str) -> ComponentHealth | None:
        """Check a single component"""
        if name not in self._checks:
            return None

        result = await self._checks[name]()
        self._last_results[name] = result
        return result

    async def check_all(self) -> HealthCheckResponse:
        """
        Run all health checks

        Returns:
            HealthCheckResponse with overall status and component details
        """
        if not self._checks:
            return HealthCheckResponse(
                status=HealthStatus.HEALTHY.value,
                timestamp=datetime.now(UTC).isoformat(),
                uptime_seconds=self.uptime_seconds,
                components={},
            )

        # Run all checks concurrently
        tasks = [self._checks[name]() for name in self._checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        components = {}
        has_critical_failure = False
        has_non_critical_failure = False

        for i, name in enumerate(self._checks.keys()):
            result = results[i]

            if isinstance(result, Exception):
                health = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(result),
                    last_check=datetime.now(UTC),
                    details={"error": type(result).__name__},
                )
            else:
                health = result

            components[name] = health.to_dict()
            self._last_results[name] = health

            # Check if critical
            is_critical = health.details.get("critical", True)
            if health.status == HealthStatus.UNHEALTHY:
                if is_critical:
                    has_critical_failure = True
                else:
                    has_non_critical_failure = True

        # Determine overall status
        if has_critical_failure:
            overall_status = HealthStatus.UNHEALTHY
        elif has_non_critical_failure:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return HealthCheckResponse(
            status=overall_status.value,
            timestamp=datetime.now(UTC).isoformat(),
            uptime_seconds=self.uptime_seconds,
            components=components,
        )

    def get_last_results(self) -> dict[str, ComponentHealth]:
        """Get last check results without running checks"""
        return self._last_results.copy()

    async def liveness(self) -> bool:
        """
        Simple liveness check (is the service running?)

        Use for Kubernetes liveness probe
        """
        return True

    async def readiness(self) -> bool:
        """
        Readiness check (is the service ready to handle requests?)

        Use for Kubernetes readiness probe
        """
        result = await self.check_all()
        return result.status != HealthStatus.UNHEALTHY.value


# Global health check instance
_health_check: HealthCheck | None = None


def get_health_check() -> HealthCheck:
    """Get global health check instance"""
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check


def register_health_check(
    name: str, check_fn: Callable[[], Awaitable[bool]], critical: bool = True
) -> None:
    """Register a health check with global instance"""
    get_health_check().register(name, check_fn, critical)
