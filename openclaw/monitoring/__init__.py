"""
Monitoring module for ClawdBot
"""

from .health import (
    ComponentHealth,
    HealthCheck,
    HealthCheckResponse,
    HealthStatus,
    get_health_check,
    register_health_check,
)
from .logger import (
    ColoredFormatter,
    JSONFormatter,
    LogContext,
    get_logger,
    log_with_context,
    setup_logging,
)
from .metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    Timer,
    counter,
    gauge,
    get_metrics,
    histogram,
)

__all__ = [
    # Health
    "HealthCheck",
    "HealthStatus",
    "ComponentHealth",
    "HealthCheckResponse",
    "get_health_check",
    "register_health_check",
    # Metrics
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "Timer",
    "get_metrics",
    "counter",
    "gauge",
    "histogram",
    # Logging
    "setup_logging",
    "get_logger",
    "JSONFormatter",
    "ColoredFormatter",
    "LogContext",
    "log_with_context",
]
