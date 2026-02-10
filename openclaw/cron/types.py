"""Cron type definitions matching TypeScript openclaw/src/cron/types.ts"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


# Schedule types
@dataclass
class AtSchedule:
    """One-time absolute timestamp schedule"""
    
    type: Literal["at"] = "at"
    timestamp: str  # ISO-8601 format


@dataclass
class EverySchedule:
    """Interval-based schedule"""
    
    type: Literal["every"] = "every"
    interval_ms: int
    anchor: str | None = None  # Optional ISO-8601 anchor point


@dataclass
class CronSchedule:
    """Cron expression schedule"""
    
    type: Literal["cron"] = "cron"
    expression: str  # e.g., "0 9 * * *"
    timezone: str | None = "UTC"


# Union type for all schedule types
CronScheduleType = AtSchedule | EverySchedule | CronSchedule


# Payload types
@dataclass
class SystemEventPayload:
    """System event payload for main session"""
    
    kind: Literal["systemEvent"] = "systemEvent"
    text: str  # System event text to enqueue


@dataclass
class AgentTurnPayload:
    """Agent turn payload for isolated sessions"""
    
    kind: Literal["agentTurn"] = "agentTurn"
    prompt: str  # Prompt to send to agent
    model: str | None = None  # Optional model override


# Union type for payloads
CronPayload = SystemEventPayload | AgentTurnPayload


# Delivery configuration
@dataclass
class CronDelivery:
    """Delivery configuration for isolated agent jobs"""
    
    channel: str  # Channel ID or "last"
    target: str | None = None  # Target user/chat ID
    best_effort: bool = False  # Continue on delivery errors


# Job state
@dataclass
class CronJobState:
    """Runtime state for cron job"""
    
    next_run_ms: int | None = None
    running_at_ms: int | None = None
    last_run_at_ms: int | None = None
    last_status: Literal["success", "error"] | None = None
    last_error: str | None = None
    last_duration_ms: int | None = None


# Main cron job definition
@dataclass
class CronJob:
    """
    Cron job definition
    
    Matches TypeScript CronJob type from openclaw/src/cron/types.ts
    """
    
    # Identity
    id: str
    agent_id: str | None = None  # Optional agent override
    
    # Metadata
    name: str = ""
    description: str | None = None
    enabled: bool = True
    delete_after_run: bool = False  # Auto-delete for one-shot jobs
    
    # Scheduling
    schedule: CronScheduleType = field(default_factory=lambda: AtSchedule(timestamp=""))
    
    # Execution
    session_target: Literal["main", "isolated"] = "main"
    wake_mode: Literal["next-heartbeat", "now"] = "next-heartbeat"
    
    # Payload
    payload: CronPayload = field(default_factory=lambda: SystemEventPayload(text=""))
    
    # Delivery (for isolated jobs)
    delivery: CronDelivery | None = None
    
    # State
    state: CronJobState = field(default_factory=CronJobState)
    
    # Metadata
    created_at_ms: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    updated_at_ms: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "enabled": self.enabled,
            "session_target": self.session_target,
            "wake_mode": self.wake_mode,
            "created_at_ms": self.created_at_ms,
            "updated_at_ms": self.updated_at_ms,
        }
        
        # Add optional fields
        if self.agent_id:
            result["agent_id"] = self.agent_id
        if self.description:
            result["description"] = self.description
        if self.delete_after_run:
            result["delete_after_run"] = self.delete_after_run
        
        # Schedule
        if isinstance(self.schedule, AtSchedule):
            result["schedule"] = {
                "type": "at",
                "timestamp": self.schedule.timestamp
            }
        elif isinstance(self.schedule, EverySchedule):
            result["schedule"] = {
                "type": "every",
                "interval_ms": self.schedule.interval_ms,
            }
            if self.schedule.anchor:
                result["schedule"]["anchor"] = self.schedule.anchor
        elif isinstance(self.schedule, CronSchedule):
            result["schedule"] = {
                "type": "cron",
                "expression": self.schedule.expression,
            }
            if self.schedule.timezone:
                result["schedule"]["timezone"] = self.schedule.timezone
        
        # Payload
        if isinstance(self.payload, SystemEventPayload):
            result["payload"] = {
                "kind": "systemEvent",
                "text": self.payload.text
            }
        elif isinstance(self.payload, AgentTurnPayload):
            result["payload"] = {
                "kind": "agentTurn",
                "prompt": self.payload.prompt,
            }
            if self.payload.model:
                result["payload"]["model"] = self.payload.model
        
        # Delivery
        if self.delivery:
            result["delivery"] = {
                "channel": self.delivery.channel,
                "best_effort": self.delivery.best_effort,
            }
            if self.delivery.target:
                result["delivery"]["target"] = self.delivery.target
        
        # State
        result["state"] = {
            k: v
            for k, v in [
                ("next_run_ms", self.state.next_run_ms),
                ("running_at_ms", self.state.running_at_ms),
                ("last_run_at_ms", self.state.last_run_at_ms),
                ("last_status", self.state.last_status),
                ("last_error", self.state.last_error),
                ("last_duration_ms", self.state.last_duration_ms),
            ]
            if v is not None
        }
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CronJob:
        """Create from dictionary"""
        # Parse schedule
        schedule_data = data.get("schedule", {})
        schedule_type = schedule_data.get("type", "at")
        
        if schedule_type == "at":
            schedule: CronScheduleType = AtSchedule(
                timestamp=schedule_data.get("timestamp", "")
            )
        elif schedule_type == "every":
            schedule = EverySchedule(
                interval_ms=schedule_data.get("interval_ms", 0),
                anchor=schedule_data.get("anchor")
            )
        elif schedule_type == "cron":
            schedule = CronSchedule(
                expression=schedule_data.get("expression", ""),
                timezone=schedule_data.get("timezone", "UTC")
            )
        else:
            schedule = AtSchedule(timestamp="")
        
        # Parse payload
        payload_data = data.get("payload", {})
        payload_kind = payload_data.get("kind", "systemEvent")
        
        if payload_kind == "systemEvent":
            payload: CronPayload = SystemEventPayload(
                text=payload_data.get("text", "")
            )
        elif payload_kind == "agentTurn":
            payload = AgentTurnPayload(
                prompt=payload_data.get("prompt", ""),
                model=payload_data.get("model")
            )
        else:
            payload = SystemEventPayload(text="")
        
        # Parse delivery
        delivery = None
        if "delivery" in data:
            delivery_data = data["delivery"]
            delivery = CronDelivery(
                channel=delivery_data.get("channel", ""),
                target=delivery_data.get("target"),
                best_effort=delivery_data.get("best_effort", False)
            )
        
        # Parse state
        state_data = data.get("state", {})
        state = CronJobState(
            next_run_ms=state_data.get("next_run_ms"),
            running_at_ms=state_data.get("running_at_ms"),
            last_run_at_ms=state_data.get("last_run_at_ms"),
            last_status=state_data.get("last_status"),
            last_error=state_data.get("last_error"),
            last_duration_ms=state_data.get("last_duration_ms"),
        )
        
        return cls(
            id=data.get("id", ""),
            agent_id=data.get("agent_id"),
            name=data.get("name", ""),
            description=data.get("description"),
            enabled=data.get("enabled", True),
            delete_after_run=data.get("delete_after_run", False),
            schedule=schedule,
            session_target=data.get("session_target", "main"),
            wake_mode=data.get("wake_mode", "next-heartbeat"),
            payload=payload,
            delivery=delivery,
            state=state,
            created_at_ms=data.get("created_at_ms", int(datetime.now().timestamp() * 1000)),
            updated_at_ms=data.get("updated_at_ms", int(datetime.now().timestamp() * 1000)),
        )
