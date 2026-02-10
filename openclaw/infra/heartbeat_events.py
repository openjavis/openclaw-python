"""Heartbeat event system (matches TypeScript infra/heartbeat-events.ts)"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class HeartbeatEventType(str, Enum):
    SENT = "sent"
    OK_EMPTY = "ok-empty"
    OK_TOKEN = "ok-token"
    SKIPPED = "skipped"
    FAILED = "failed"


class IndicatorType(str, Enum):
    HEARTBEAT = "heartbeat"
    ALERT = "alert"
    OK = "ok"
    NONE = "none"


@dataclass
class HeartbeatEvent:
    """A single heartbeat event"""
    event_type: HeartbeatEventType
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    reason: str | None = None
    metadata: dict[str, Any] | None = None


# Global event storage
_last_events: dict[str, HeartbeatEvent] = {}
_listeners: list[Callable[[HeartbeatEvent], Any]] = []


def emit_heartbeat_event(event: HeartbeatEvent) -> None:
    """Emit a heartbeat event"""
    _last_events[event.agent_id] = event
    logger.debug(f"Heartbeat event: {event.event_type} for agent {event.agent_id}")
    
    for listener in _listeners:
        try:
            result = listener(event)
            if asyncio.iscoroutine(result):
                asyncio.ensure_future(result)
        except Exception as e:
            logger.error(f"Heartbeat listener error: {e}")


def on_heartbeat_event(listener: Callable[[HeartbeatEvent], Any]) -> Callable:
    """Subscribe to heartbeat events. Returns unsubscribe function."""
    _listeners.append(listener)
    
    def unsubscribe():
        if listener in _listeners:
            _listeners.remove(listener)
    
    return unsubscribe


def get_last_heartbeat_event(agent_id: str) -> HeartbeatEvent | None:
    """Get the last heartbeat event for an agent"""
    return _last_events.get(agent_id)


def resolve_indicator_type(event_type: HeartbeatEventType) -> IndicatorType:
    """Map heartbeat event type to indicator type"""
    mapping = {
        HeartbeatEventType.SENT: IndicatorType.HEARTBEAT,
        HeartbeatEventType.OK_EMPTY: IndicatorType.OK,
        HeartbeatEventType.OK_TOKEN: IndicatorType.OK,
        HeartbeatEventType.SKIPPED: IndicatorType.NONE,
        HeartbeatEventType.FAILED: IndicatorType.ALERT,
    }
    return mapping.get(event_type, IndicatorType.NONE)
