"""Diagnostic event system (matches TypeScript infra/diagnostic-events.ts)"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DiagnosticFlag(str, Enum):
    """Diagnostic flags for feature tracking"""
    HEARTBEAT_ENABLED = "heartbeat_enabled"
    DISCOVERY_ENABLED = "discovery_enabled"
    TAILSCALE_ENABLED = "tailscale_enabled"
    BROWSER_ENABLED = "browser_enabled"
    CRON_ENABLED = "cron_enabled"
    TTS_ENABLED = "tts_enabled"


@dataclass
class DiagnosticStats:
    """Diagnostic statistics snapshot"""
    webhooks_received: int = 0
    webhooks_processed: int = 0
    webhooks_errors: int = 0
    messages_queued: int = 0
    messages_processed: int = 0
    sessions_idle: int = 0
    sessions_processing: int = 0
    sessions_waiting: int = 0
    active_runs: int = 0
    stuck_sessions: int = 0
    uptime_seconds: float = 0.0


# Global diagnostic state
_stats = DiagnosticStats()
_start_time = datetime.now()
_flags: dict[str, bool] = {}
_listeners: list[Callable[[str, Any], Any]] = []
_heartbeat_task: asyncio.Task | None = None


def log_webhook_received(channel: str, metadata: dict[str, Any] | None = None) -> None:
    """Log webhook receipt"""
    _stats.webhooks_received += 1
    _emit("webhook.received", {"channel": channel, **(metadata or {})})


def log_webhook_processed(channel: str, duration_ms: float) -> None:
    """Log webhook processing completion"""
    _stats.webhooks_processed += 1
    _emit("webhook.processed", {"channel": channel, "duration_ms": duration_ms})


def log_webhook_error(channel: str, error: str) -> None:
    """Log webhook error"""
    _stats.webhooks_errors += 1
    _emit("webhook.error", {"channel": channel, "error": error})


def log_message_queued(session_key: str) -> None:
    """Log message queued"""
    _stats.messages_queued += 1
    _emit("message.queued", {"session_key": session_key})


def log_message_processed(session_key: str, duration_ms: float) -> None:
    """Log message processed"""
    _stats.messages_processed += 1
    _emit("message.processed", {"session_key": session_key, "duration_ms": duration_ms})


def log_session_state_change(
    session_key: str,
    old_state: str,
    new_state: str,
) -> None:
    """Log session state transition"""
    if new_state == "idle":
        _stats.sessions_idle += 1
        _stats.sessions_processing = max(0, _stats.sessions_processing - 1)
    elif new_state == "processing":
        _stats.sessions_processing += 1
        _stats.sessions_idle = max(0, _stats.sessions_idle - 1)
    elif new_state == "waiting":
        _stats.sessions_waiting += 1
    
    _emit("session.state_change", {
        "session_key": session_key,
        "old_state": old_state,
        "new_state": new_state,
    })


def log_session_stuck(session_key: str, duration_sec: float) -> None:
    """Log stuck session detection"""
    _stats.stuck_sessions += 1
    _emit("session.stuck", {
        "session_key": session_key,
        "duration_sec": duration_sec,
    })
    logger.warning(f"Stuck session detected: {session_key} ({duration_sec}s)")


def log_lane_enqueue(lane: str, session_key: str) -> None:
    """Log lane enqueue"""
    _emit("lane.enqueue", {"lane": lane, "session_key": session_key})


def log_lane_dequeue(lane: str, session_key: str) -> None:
    """Log lane dequeue"""
    _emit("lane.dequeue", {"lane": lane, "session_key": session_key})


def log_run_attempt(session_key: str, model: str) -> None:
    """Log run attempt"""
    _stats.active_runs += 1
    _emit("run.attempt", {"session_key": session_key, "model": model})


def log_active_runs(count: int) -> None:
    """Log active run count"""
    _stats.active_runs = count
    _emit("runs.active", {"count": count})


def set_diagnostic_flag(flag: str, value: bool) -> None:
    """Set a diagnostic flag"""
    _flags[flag] = value


def get_diagnostic_flag(flag: str) -> bool:
    """Get a diagnostic flag"""
    return _flags.get(flag, False)


def get_diagnostic_stats() -> DiagnosticStats:
    """Get current diagnostic statistics"""
    _stats.uptime_seconds = (datetime.now() - _start_time).total_seconds()
    return _stats


def on_diagnostic_event(listener: Callable[[str, Any], Any]) -> Callable:
    """Subscribe to diagnostic events"""
    _listeners.append(listener)
    
    def unsubscribe():
        if listener in _listeners:
            _listeners.remove(listener)
    
    return unsubscribe


def _emit(event_type: str, data: dict[str, Any]) -> None:
    """Emit a diagnostic event"""
    for listener in _listeners:
        try:
            result = listener(event_type, data)
            if asyncio.iscoroutine(result):
                asyncio.ensure_future(result)
        except Exception as e:
            logger.error(f"Diagnostic listener error: {e}")


async def _diagnostic_heartbeat_loop(interval_sec: float = 30.0) -> None:
    """Periodic diagnostic heartbeat (logs stats every interval)"""
    while True:
        try:
            await asyncio.sleep(interval_sec)
            
            stats = get_diagnostic_stats()
            logger.debug(
                f"Diagnostic heartbeat: "
                f"webhooks={stats.webhooks_received}/{stats.webhooks_processed}, "
                f"messages={stats.messages_queued}/{stats.messages_processed}, "
                f"sessions=idle:{stats.sessions_idle}/proc:{stats.sessions_processing}/"
                f"wait:{stats.sessions_waiting}, "
                f"runs={stats.active_runs}, stuck={stats.stuck_sessions}, "
                f"uptime={stats.uptime_seconds:.0f}s"
            )
            
            _emit("heartbeat", {
                "stats": {
                    "webhooks_received": stats.webhooks_received,
                    "webhooks_processed": stats.webhooks_processed,
                    "messages_queued": stats.messages_queued,
                    "messages_processed": stats.messages_processed,
                    "active_runs": stats.active_runs,
                    "uptime_seconds": stats.uptime_seconds,
                }
            })
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Diagnostic heartbeat error: {e}")


def start_diagnostic_heartbeat(interval_sec: float = 30.0) -> None:
    """Start diagnostic heartbeat"""
    global _heartbeat_task
    if _heartbeat_task is None or _heartbeat_task.done():
        _heartbeat_task = asyncio.create_task(
            _diagnostic_heartbeat_loop(interval_sec)
        )
        logger.info(f"Diagnostic heartbeat started (interval: {interval_sec}s)")


def stop_diagnostic_heartbeat() -> None:
    """Stop diagnostic heartbeat"""
    global _heartbeat_task
    if _heartbeat_task and not _heartbeat_task.done():
        _heartbeat_task.cancel()
        logger.info("Diagnostic heartbeat stopped")
    _heartbeat_task = None
