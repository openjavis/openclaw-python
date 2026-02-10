"""OpenTelemetry integration (matches TypeScript extensions/diagnostics-otel/)

Exports metrics, traces, and logs to OTLP backends (Jaeger, Prometheus, Datadog, etc.)
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# OpenTelemetry SDK availability
_OTEL_AVAILABLE = False
try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    
    _OTEL_AVAILABLE = True
except ImportError:
    logger.warning("OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http")


class OpenTelemetryService:
    """
    OpenTelemetry service for exporting metrics, traces, and logs.
    
    Matches TypeScript diagnostics-otel plugin functionality.
    """
    
    def __init__(
        self,
        service_name: str = "openclaw-python",
        endpoint: str | None = None,
        enabled: bool = True,
        flush_interval_ms: int = 60000,
    ):
        self.service_name = service_name
        self.endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
        self.enabled = enabled and _OTEL_AVAILABLE
        self.flush_interval_ms = flush_interval_ms
        
        self._meter_provider: Any = None
        self._tracer_provider: Any = None
        self._meter: Any = None
        self._tracer: Any = None
        
        # Metric instruments
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}
        
        if self.enabled:
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize OpenTelemetry providers"""
        if not _OTEL_AVAILABLE:
            logger.error("Cannot initialize OpenTelemetry: SDK not installed")
            self.enabled = False
            return
        
        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
            })
            
            # Metrics
            metric_exporter = OTLPMetricExporter(
                endpoint=f"{self.endpoint}/v1/metrics",
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=self.flush_interval_ms,
            )
            self._meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )
            metrics.set_meter_provider(self._meter_provider)
            self._meter = self._meter_provider.get_meter("openclaw")
            
            # Traces
            trace_exporter = OTLPSpanExporter(
                endpoint=f"{self.endpoint}/v1/traces",
            )
            self._tracer_provider = TracerProvider(resource=resource)
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(trace_exporter)
            )
            trace.set_tracer_provider(self._tracer_provider)
            self._tracer = self._tracer_provider.get_tracer("openclaw")
            
            # Create metric instruments
            self._create_instruments()
            
            logger.info(f"OpenTelemetry initialized: endpoint={self.endpoint}")
        
        except Exception as e:
            logger.error(f"OpenTelemetry initialization failed: {e}")
            self.enabled = False
    
    def _create_instruments(self) -> None:
        """Create all metric instruments"""
        if not self._meter:
            return
        
        # Counters
        self._counters["tokens"] = self._meter.create_counter(
            "openclaw.tokens",
            description="Token usage by type (input/output/cache)",
        )
        self._counters["cost"] = self._meter.create_counter(
            "openclaw.cost.usd",
            description="Estimated model costs in USD",
        )
        self._counters["webhook.received"] = self._meter.create_counter(
            "openclaw.webhook.received",
            description="Webhooks received",
        )
        self._counters["webhook.error"] = self._meter.create_counter(
            "openclaw.webhook.error",
            description="Webhook errors",
        )
        self._counters["message.queued"] = self._meter.create_counter(
            "openclaw.message.queued",
            description="Messages queued",
        )
        self._counters["message.processed"] = self._meter.create_counter(
            "openclaw.message.processed",
            description="Messages processed",
        )
        self._counters["session.state"] = self._meter.create_counter(
            "openclaw.session.state",
            description="Session state transitions",
        )
        self._counters["session.stuck"] = self._meter.create_counter(
            "openclaw.session.stuck",
            description="Stuck sessions detected",
        )
        self._counters["run.attempt"] = self._meter.create_counter(
            "openclaw.run.attempt",
            description="Agent run attempts",
        )
        
        # Histograms
        self._histograms["run.duration"] = self._meter.create_histogram(
            "openclaw.run.duration_ms",
            description="Agent run duration in milliseconds",
        )
        self._histograms["context.tokens"] = self._meter.create_histogram(
            "openclaw.context.tokens",
            description="Context window token usage",
        )
        self._histograms["webhook.duration"] = self._meter.create_histogram(
            "openclaw.webhook.duration_ms",
            description="Webhook processing duration",
        )
        self._histograms["message.duration"] = self._meter.create_histogram(
            "openclaw.message.duration_ms",
            description="Message processing duration",
        )
    
    def record_tokens(
        self,
        count: int,
        token_type: str = "total",
        model: str = "unknown",
        provider: str = "unknown",
    ) -> None:
        """Record token usage"""
        if not self.enabled or "tokens" not in self._counters:
            return
        
        self._counters["tokens"].add(
            count,
            {"type": token_type, "model": model, "provider": provider},
        )
    
    def record_cost(
        self,
        cost_usd: float,
        model: str = "unknown",
        provider: str = "unknown",
    ) -> None:
        """Record model cost"""
        if not self.enabled or "cost" not in self._counters:
            return
        
        self._counters["cost"].add(
            cost_usd,
            {"model": model, "provider": provider},
        )
    
    def record_run_duration(
        self,
        duration_ms: float,
        model: str = "unknown",
        success: bool = True,
    ) -> None:
        """Record agent run duration"""
        if not self.enabled or "run.duration" not in self._histograms:
            return
        
        self._histograms["run.duration"].record(
            duration_ms,
            {"model": model, "success": str(success)},
        )
    
    def record_webhook(
        self,
        channel: str,
        duration_ms: float | None = None,
        error: bool = False,
    ) -> None:
        """Record webhook event"""
        if not self.enabled:
            return
        
        if error and "webhook.error" in self._counters:
            self._counters["webhook.error"].add(1, {"channel": channel})
        elif "webhook.received" in self._counters:
            self._counters["webhook.received"].add(1, {"channel": channel})
        
        if duration_ms and "webhook.duration" in self._histograms:
            self._histograms["webhook.duration"].record(
                duration_ms,
                {"channel": channel},
            )
    
    def record_message(
        self,
        queued: bool = True,
        duration_ms: float | None = None,
    ) -> None:
        """Record message processing"""
        if not self.enabled:
            return
        
        if queued and "message.queued" in self._counters:
            self._counters["message.queued"].add(1)
        elif "message.processed" in self._counters:
            self._counters["message.processed"].add(1)
        
        if duration_ms and "message.duration" in self._histograms:
            self._histograms["message.duration"].record(duration_ms)
    
    def record_session_state(
        self,
        old_state: str,
        new_state: str,
        session_key: str = "unknown",
    ) -> None:
        """Record session state transition"""
        if not self.enabled or "session.state" not in self._counters:
            return
        
        self._counters["session.state"].add(
            1,
            {"old_state": old_state, "new_state": new_state},
        )
    
    def record_stuck_session(
        self,
        age_ms: float,
        session_key: str = "unknown",
    ) -> None:
        """Record stuck session"""
        if not self.enabled or "session.stuck" not in self._counters:
            return
        
        self._counters["session.stuck"].add(1)
    
    def start_span(self, name: str, attributes: dict[str, Any] | None = None):
        """Start a trace span (context manager)"""
        if not self.enabled or not self._tracer:
            # No-op context manager
            from contextlib import nullcontext
            return nullcontext()
        
        return self._tracer.start_as_current_span(
            name,
            attributes=attributes or {},
        )
    
    def shutdown(self) -> None:
        """Shutdown OpenTelemetry providers"""
        if self._meter_provider:
            self._meter_provider.shutdown()
        if self._tracer_provider:
            self._tracer_provider.shutdown()
        logger.info("OpenTelemetry shut down")


# Global service instance
_service: OpenTelemetryService | None = None


def initialize_otel(
    service_name: str = "openclaw-python",
    endpoint: str | None = None,
    enabled: bool = True,
) -> OpenTelemetryService:
    """Initialize global OpenTelemetry service"""
    global _service
    _service = OpenTelemetryService(
        service_name=service_name,
        endpoint=endpoint,
        enabled=enabled,
    )
    return _service


def get_otel_service() -> OpenTelemetryService | None:
    """Get global OpenTelemetry service"""
    return _service


def shutdown_otel() -> None:
    """Shutdown global OpenTelemetry service"""
    if _service:
        _service.shutdown()
