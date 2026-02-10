"""Diagnostic logging (matches TypeScript logging/diagnostic.ts)

Re-exports diagnostic functions from infra module for backward compatibility.
"""

from ..infra.diagnostic_events import (
    log_webhook_received,
    log_webhook_processed,
    log_webhook_error,
    log_message_queued,
    log_message_processed,
    log_session_state_change,
    log_session_stuck,
    log_lane_enqueue,
    log_lane_dequeue,
    log_run_attempt,
    log_active_runs,
    get_diagnostic_stats,
    start_diagnostic_heartbeat,
    stop_diagnostic_heartbeat,
    on_diagnostic_event,
    set_diagnostic_flag,
    get_diagnostic_flag,
)

__all__ = [
    "log_webhook_received",
    "log_webhook_processed",
    "log_webhook_error",
    "log_message_queued",
    "log_message_processed",
    "log_session_state_change",
    "log_session_stuck",
    "log_lane_enqueue",
    "log_lane_dequeue",
    "log_run_attempt",
    "log_active_runs",
    "get_diagnostic_stats",
    "start_diagnostic_heartbeat",
    "stop_diagnostic_heartbeat",
    "on_diagnostic_event",
    "set_diagnostic_flag",
    "get_diagnostic_flag",
]
