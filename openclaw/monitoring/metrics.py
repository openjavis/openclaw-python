"""
Metrics collection for ClawdBot
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class Counter:
    """Simple counter metric"""

    name: str
    description: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def inc(self, value: float = 1.0) -> None:
        """Increment counter"""
        with self._lock:
            self._value += value

    @property
    def value(self) -> float:
        """Get current value"""
        return self._value

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "type": "counter",
            "description": self.description,
            "labels": self.labels,
            "value": self._value,
        }


@dataclass
class Gauge:
    """Gauge metric (can go up and down)"""

    name: str
    description: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    _value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def set(self, value: float) -> None:
        """Set gauge value"""
        with self._lock:
            self._value = value

    def inc(self, value: float = 1.0) -> None:
        """Increment gauge"""
        with self._lock:
            self._value += value

    def dec(self, value: float = 1.0) -> None:
        """Decrement gauge"""
        with self._lock:
            self._value -= value

    @property
    def value(self) -> float:
        """Get current value"""
        return self._value

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "type": "gauge",
            "description": self.description,
            "labels": self.labels,
            "value": self._value,
        }


@dataclass
class Histogram:
    """Histogram metric for measuring distributions"""

    name: str
    description: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    buckets: list[float] = field(
        default_factory=lambda: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    _values: list[float] = field(default_factory=list)
    _sum: float = 0.0
    _count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def observe(self, value: float) -> None:
        """Record an observation"""
        with self._lock:
            self._values.append(value)
            self._sum += value
            self._count += 1

            # Keep last 1000 values for percentile calculation
            if len(self._values) > 1000:
                self._values = self._values[-1000:]

    @property
    def count(self) -> int:
        """Get observation count"""
        return self._count

    @property
    def sum(self) -> float:
        """Get sum of observations"""
        return self._sum

    @property
    def avg(self) -> float:
        """Get average"""
        if self._count == 0:
            return 0.0
        return self._sum / self._count

    def percentile(self, p: float) -> float:
        """Get percentile value (0-100)"""
        with self._lock:
            if not self._values:
                return 0.0

            sorted_values = sorted(self._values)
            idx = int(len(sorted_values) * p / 100)
            return sorted_values[min(idx, len(sorted_values) - 1)]

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "type": "histogram",
            "description": self.description,
            "labels": self.labels,
            "count": self._count,
            "sum": self._sum,
            "avg": self.avg,
            "p50": self.percentile(50),
            "p95": self.percentile(95),
            "p99": self.percentile(99),
        }


class Timer:
    """Context manager for timing operations"""

    def __init__(self, histogram: Histogram):
        self._histogram = histogram
        self._start: float | None = None

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._start:
            elapsed = time.time() - self._start
            self._histogram.observe(elapsed)
        return False

    async def __aenter__(self):
        self._start = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._start:
            elapsed = time.time() - self._start
            self._histogram.observe(elapsed)
        return False


class MetricsCollector:
    """
    Central metrics collector

    Example usage:
        metrics = MetricsCollector()

        # Create metrics
        requests = metrics.counter("http_requests_total", "Total HTTP requests")
        active = metrics.gauge("active_connections", "Active connections")
        latency = metrics.histogram("request_latency_seconds", "Request latency")

        # Use metrics
        requests.inc()
        active.set(10)

        with latency.time():
            await process_request()

        # Get all metrics
        all_metrics = metrics.to_dict()
    """

    def __init__(self):
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._lock = threading.Lock()
        self._start_time = datetime.now(UTC)

    def counter(
        self, name: str, description: str = "", labels: dict[str, str] | None = None
    ) -> Counter:
        """Get or create a counter"""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._counters:
                self._counters[key] = Counter(
                    name=name, description=description, labels=labels or {}
                )
            return self._counters[key]

    def gauge(
        self, name: str, description: str = "", labels: dict[str, str] | None = None
    ) -> Gauge:
        """Get or create a gauge"""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = Gauge(name=name, description=description, labels=labels or {})
            return self._gauges[key]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ) -> Histogram:
        """Get or create a histogram"""
        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = Histogram(
                    name=name,
                    description=description,
                    labels=labels or {},
                    buckets=buckets
                    or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
                )
            return self._histograms[key]

    def timer(self, name: str, description: str = "") -> Timer:
        """Create a timer context manager"""
        histogram = self.histogram(name, description)
        return Timer(histogram)

    def _make_key(self, name: str, labels: dict[str, str] | None) -> str:
        """Create unique key for metric with labels"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def to_dict(self) -> dict:
        """Convert all metrics to dictionary"""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": (datetime.now(UTC) - self._start_time).total_seconds(),
            "counters": {k: v.to_dict() for k, v in self._counters.items()},
            "gauges": {k: v.to_dict() for k, v in self._gauges.items()},
            "histograms": {k: v.to_dict() for k, v in self._histograms.items()},
        }

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        # Counters
        for counter in self._counters.values():
            labels = self._format_labels(counter.labels)
            lines.append(f"# HELP {counter.name} {counter.description}")
            lines.append(f"# TYPE {counter.name} counter")
            lines.append(f"{counter.name}{labels} {counter.value}")

        # Gauges
        for gauge in self._gauges.values():
            labels = self._format_labels(gauge.labels)
            lines.append(f"# HELP {gauge.name} {gauge.description}")
            lines.append(f"# TYPE {gauge.name} gauge")
            lines.append(f"{gauge.name}{labels} {gauge.value}")

        # Histograms
        for hist in self._histograms.values():
            labels = self._format_labels(hist.labels)
            lines.append(f"# HELP {hist.name} {hist.description}")
            lines.append(f"# TYPE {hist.name} histogram")
            lines.append(f"{hist.name}_count{labels} {hist.count}")
            lines.append(f"{hist.name}_sum{labels} {hist.sum}")

        return "\n".join(lines)

    def _format_labels(self, labels: dict[str, str]) -> str:
        """Format labels for Prometheus"""
        if not labels:
            return ""
        parts = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(parts) + "}"

    def reset(self) -> None:
        """Reset all metrics"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


# Global metrics instance
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get global metrics collector"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


# Convenience functions
def counter(name: str, description: str = "") -> Counter:
    """Create or get a counter from global collector"""
    return get_metrics().counter(name, description)


def gauge(name: str, description: str = "") -> Gauge:
    """Create or get a gauge from global collector"""
    return get_metrics().gauge(name, description)


def histogram(name: str, description: str = "") -> Histogram:
    """Create or get a histogram from global collector"""
    return get_metrics().histogram(name, description)
