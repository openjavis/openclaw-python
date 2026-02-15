"""
Cron Job Serialization - converts Python snake_case to TypeScript camelCase

Ensures complete compatibility with openclaw TypeScript frontend
"""
from __future__ import annotations

from typing import Any


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_schedule_to_api(schedule_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Convert schedule dict to TypeScript format
    
    TypeScript format:
    - { kind: "at", at: "ISO-8601" }
    - { kind: "every", everyMs: number, anchorMs?: number }
    - { kind: "cron", expr: string, tz?: string }
    """
    schedule_type = schedule_dict.get("type")
    
    if schedule_type == "at":
        return {
            "kind": "at",
            "at": schedule_dict.get("timestamp", "")
        }
    elif schedule_type == "every":
        result = {
            "kind": "every",
            "everyMs": schedule_dict.get("interval_ms", 0)
        }
        if schedule_dict.get("anchor"):
            # Convert anchor from ISO string to ms timestamp if needed
            anchor = schedule_dict.get("anchor")
            if isinstance(anchor, str):
                # Parse ISO string to timestamp
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(anchor.replace('Z', '+00:00'))
                    result["anchorMs"] = int(dt.timestamp() * 1000)
                except:
                    # If already a number, use as-is
                    result["anchorMs"] = anchor
            else:
                result["anchorMs"] = anchor
        return result
    elif schedule_type == "cron":
        result = {
            "kind": "cron",
            "expr": schedule_dict.get("expression", "")
        }
        if schedule_dict.get("timezone"):
            result["tz"] = schedule_dict["timezone"]
        return result
    
    return schedule_dict


def convert_payload_to_api(payload_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Convert payload dict to TypeScript format
    
    TypeScript format:
    - { kind: "systemEvent", text: string }
    - { kind: "agentTurn", message: string, model?: string, ... }
    """
    kind = payload_dict.get("kind")
    
    if kind == "systemEvent":
        return {
            "kind": "systemEvent",
            "text": payload_dict.get("text", "")
        }
    elif kind == "agentTurn":
        result = {
            "kind": "agentTurn",
            "message": payload_dict.get("prompt", "")  # prompt → message
        }
        # Optional fields
        for field in ["model", "thinking", "timeoutSeconds", "deliver", "channel", "to"]:
            if field in payload_dict:
                result[field] = payload_dict[field]
        return result
    
    return payload_dict


def convert_delivery_to_api(delivery_dict: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Convert delivery dict to TypeScript format
    
    TypeScript format:
    - { mode: "none" | "announce", channel?: string, to?: string, bestEffort?: boolean }
    """
    if not delivery_dict:
        return None
    
    result = {
        "mode": delivery_dict.get("mode", "none")
    }
    
    if delivery_dict.get("channel"):
        result["channel"] = delivery_dict["channel"]
    
    # target → to
    if delivery_dict.get("target"):
        result["to"] = delivery_dict["target"]
    elif delivery_dict.get("to"):
        result["to"] = delivery_dict["to"]
    
    # best_effort → bestEffort
    if "best_effort" in delivery_dict:
        result["bestEffort"] = delivery_dict["best_effort"]
    elif "bestEffort" in delivery_dict:
        result["bestEffort"] = delivery_dict["bestEffort"]
    
    return result


def convert_state_to_api(state_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Convert state dict to TypeScript format
    
    TypeScript format:
    - { nextRunAtMs?: number, runningAtMs?: number, lastRunAtMs?: number,
        lastStatus?: "ok" | "error" | "skipped", lastError?: string, lastDurationMs?: number }
    """
    result = {}
    
    # Convert field names
    field_mapping = {
        "next_run_ms": "nextRunAtMs",
        "running_at_ms": "runningAtMs",
        "last_run_at_ms": "lastRunAtMs",
        "last_status": "lastStatus",
        "last_error": "lastError",
        "last_duration_ms": "lastDurationMs",
    }
    
    for py_name, ts_name in field_mapping.items():
        if py_name in state_dict and state_dict[py_name] is not None:
            value = state_dict[py_name]
            # Convert "success" to "ok"
            if py_name == "last_status" and value == "success":
                value = "ok"
            result[ts_name] = value
    
    return result


def convert_job_to_api(job_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Convert full CronJob dict to TypeScript API format
    
    This is the master conversion function that ensures complete compatibility
    """
    result = {
        "id": job_dict.get("id", ""),
        "name": job_dict.get("name", ""),
        "enabled": job_dict.get("enabled", True),
    }
    
    # Optional string fields
    if job_dict.get("agent_id"):
        result["agentId"] = job_dict["agent_id"]
    if job_dict.get("description"):
        result["description"] = job_dict["description"]
    
    # Boolean fields
    if job_dict.get("delete_after_run"):
        result["deleteAfterRun"] = job_dict["delete_after_run"]
    
    # Timestamp fields (ms)
    if "created_at_ms" in job_dict:
        result["createdAtMs"] = job_dict["created_at_ms"]
    if "updated_at_ms" in job_dict:
        result["updatedAtMs"] = job_dict["updated_at_ms"]
    
    # Session target
    result["sessionTarget"] = job_dict.get("session_target", "isolated")
    
    # Wake mode
    result["wakeMode"] = job_dict.get("wake_mode", "next-heartbeat")
    
    # Schedule (convert)
    if "schedule" in job_dict:
        result["schedule"] = convert_schedule_to_api(job_dict["schedule"])
    
    # Payload (convert)
    if "payload" in job_dict:
        result["payload"] = convert_payload_to_api(job_dict["payload"])
    
    # Delivery (convert)
    if job_dict.get("delivery"):
        result["delivery"] = convert_delivery_to_api(job_dict["delivery"])
    
    # State (convert)
    if "state" in job_dict:
        result["state"] = convert_state_to_api(job_dict["state"])
    
    # Add computed fields for frontend
    if result.get("state", {}).get("nextRunAtMs"):
        from datetime import datetime, UTC
        try:
            ts = result["state"]["nextRunAtMs"] / 1000
            dt = datetime.fromtimestamp(ts, UTC)
            result["nextRun"] = dt.isoformat()
        except:
            pass
    
    if result.get("state", {}).get("lastRunAtMs"):
        from datetime import datetime, UTC
        try:
            ts = result["state"]["lastRunAtMs"] / 1000
            dt = datetime.fromtimestamp(ts, UTC)
            result["lastRun"] = dt.isoformat()
        except:
            pass
    
    result["running"] = result.get("state", {}).get("runningAtMs") is not None
    
    return result


def convert_run_log_entry_to_api(entry_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Convert run log entry to TypeScript format
    
    TypeScript format:
    - { ts: number, jobId: string, action: "finished", status?: "ok" | "error" | "skipped",
        error?: string, summary?: string, runAtMs?: number, durationMs?: number, nextRunAtMs?: number }
    """
    result = {
        "ts": entry_dict.get("timestamp", 0),
        "jobId": entry_dict.get("job_id", ""),
        "action": entry_dict.get("action", "finished"),
    }
    
    # Optional fields
    if "status" in entry_dict:
        status = entry_dict["status"]
        # Convert "success" to "ok"
        if status == "success":
            status = "ok"
        result["status"] = status
    
    if entry_dict.get("error"):
        result["error"] = entry_dict["error"]
    if entry_dict.get("summary"):
        result["summary"] = entry_dict["summary"]
    if entry_dict.get("run_at_ms"):
        result["runAtMs"] = entry_dict["run_at_ms"]
    if entry_dict.get("duration_ms"):
        result["durationMs"] = entry_dict["duration_ms"]
    if entry_dict.get("next_run_at_ms"):
        result["nextRunAtMs"] = entry_dict["next_run_at_ms"]
    
    return result


__all__ = [
    "to_camel_case",
    "convert_schedule_to_api",
    "convert_payload_to_api",
    "convert_delivery_to_api",
    "convert_state_to_api",
    "convert_job_to_api",
    "convert_run_log_entry_to_api",
]
