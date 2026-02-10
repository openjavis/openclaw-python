"""Heartbeat runner (matches TypeScript infra/heartbeat-runner.ts)

Periodically sends heartbeat messages to agents to trigger proactive behavior.
Supports:
- Multi-agent with per-agent intervals
- Active hours (timezone-aware)
- Queue-aware (skips if requests in flight)
- Duplicate suppression (24h window)
- Delivery target resolution
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from .heartbeat_events import (
    HeartbeatEvent,
    HeartbeatEventType,
    emit_heartbeat_event,
)

logger = logging.getLogger(__name__)

# Global state
_heartbeats_enabled = True
_running_tasks: dict[str, asyncio.Task] = {}
_last_sent: dict[str, datetime] = {}
_suppression_window = timedelta(hours=24)


def set_heartbeats_enabled(enabled: bool) -> None:
    """Globally enable/disable heartbeats"""
    global _heartbeats_enabled
    _heartbeats_enabled = enabled
    logger.info(f"Heartbeats {'enabled' if enabled else 'disabled'}")


def is_heartbeat_enabled_for_agent(
    agent_config: dict[str, Any],
) -> bool:
    """Check if heartbeat is enabled for a specific agent"""
    if not _heartbeats_enabled:
        return False
    
    heartbeat_config = agent_config.get("heartbeat", {})
    return heartbeat_config.get("enabled", False)


def resolve_heartbeat_interval_ms(
    agent_config: dict[str, Any],
) -> int:
    """Resolve heartbeat interval in milliseconds"""
    heartbeat_config = agent_config.get("heartbeat", {})
    interval = heartbeat_config.get("interval", "1h")
    
    # Parse duration string
    if isinstance(interval, (int, float)):
        return int(interval)
    
    multipliers = {"s": 1000, "m": 60_000, "h": 3_600_000, "d": 86_400_000}
    
    for suffix, mult in multipliers.items():
        if interval.endswith(suffix):
            try:
                return int(float(interval[:-1]) * mult)
            except ValueError:
                pass
    
    return 3_600_000  # Default 1 hour


def resolve_heartbeat_prompt(
    agent_config: dict[str, Any],
) -> str:
    """Resolve heartbeat prompt text"""
    heartbeat_config = agent_config.get("heartbeat", {})
    return heartbeat_config.get(
        "prompt",
        "This is a scheduled heartbeat. Check for any pending tasks, reminders, "
        "or proactive actions you should take. If nothing needs attention, respond briefly."
    )


def _is_within_active_hours(
    agent_config: dict[str, Any],
) -> bool:
    """Check if current time is within active hours"""
    heartbeat_config = agent_config.get("heartbeat", {})
    active_hours = heartbeat_config.get("activeHours")
    
    if not active_hours:
        return True  # No restriction
    
    now = datetime.now()
    start_hour = active_hours.get("start", 0)
    end_hour = active_hours.get("end", 24)
    
    current_hour = now.hour
    
    if start_hour <= end_hour:
        return start_hour <= current_hour < end_hour
    else:
        # Overnight range (e.g., 22-6)
        return current_hour >= start_hour or current_hour < end_hour


def _should_suppress(agent_id: str) -> bool:
    """Check if heartbeat should be suppressed (duplicate within window)"""
    last = _last_sent.get(agent_id)
    if last is None:
        return False
    return datetime.now() - last < _suppression_window


async def run_heartbeat_once(
    agent_id: str,
    agent_config: dict[str, Any],
    execute_fn: Callable[[str, str], Any],
    is_busy_fn: Callable[[str], bool] | None = None,
) -> None:
    """Execute a single heartbeat for an agent"""
    
    # Check if enabled
    if not is_heartbeat_enabled_for_agent(agent_config):
        emit_heartbeat_event(HeartbeatEvent(
            event_type=HeartbeatEventType.SKIPPED,
            agent_id=agent_id,
            reason="disabled",
        ))
        return
    
    # Check active hours
    if not _is_within_active_hours(agent_config):
        emit_heartbeat_event(HeartbeatEvent(
            event_type=HeartbeatEventType.SKIPPED,
            agent_id=agent_id,
            reason="outside_active_hours",
        ))
        return
    
    # Check if agent is busy (queue-aware)
    if is_busy_fn and is_busy_fn(agent_id):
        emit_heartbeat_event(HeartbeatEvent(
            event_type=HeartbeatEventType.SKIPPED,
            agent_id=agent_id,
            reason="agent_busy",
        ))
        return
    
    # Check duplicate suppression
    if _should_suppress(agent_id):
        emit_heartbeat_event(HeartbeatEvent(
            event_type=HeartbeatEventType.SKIPPED,
            agent_id=agent_id,
            reason="suppressed",
        ))
        return
    
    # Send heartbeat
    prompt = resolve_heartbeat_prompt(agent_config)
    
    try:
        emit_heartbeat_event(HeartbeatEvent(
            event_type=HeartbeatEventType.SENT,
            agent_id=agent_id,
        ))
        
        _last_sent[agent_id] = datetime.now()
        
        result = await execute_fn(agent_id, prompt)
        
        # Determine outcome
        if result:
            emit_heartbeat_event(HeartbeatEvent(
                event_type=HeartbeatEventType.OK_TOKEN,
                agent_id=agent_id,
            ))
        else:
            emit_heartbeat_event(HeartbeatEvent(
                event_type=HeartbeatEventType.OK_EMPTY,
                agent_id=agent_id,
            ))
    
    except Exception as e:
        logger.error(f"Heartbeat failed for agent {agent_id}: {e}")
        emit_heartbeat_event(HeartbeatEvent(
            event_type=HeartbeatEventType.FAILED,
            agent_id=agent_id,
            reason=str(e),
        ))


async def _heartbeat_loop(
    agent_id: str,
    agent_config: dict[str, Any],
    execute_fn: Callable[[str, str], Any],
    is_busy_fn: Callable[[str], bool] | None = None,
) -> None:
    """Internal heartbeat loop for an agent"""
    interval_ms = resolve_heartbeat_interval_ms(agent_config)
    interval_sec = interval_ms / 1000.0
    
    logger.info(f"Heartbeat loop started for agent {agent_id} (interval: {interval_sec}s)")
    
    while True:
        try:
            await asyncio.sleep(interval_sec)
            
            if not _heartbeats_enabled:
                continue
            
            await run_heartbeat_once(agent_id, agent_config, execute_fn, is_busy_fn)
        
        except asyncio.CancelledError:
            logger.info(f"Heartbeat loop cancelled for agent {agent_id}")
            break
        except Exception as e:
            logger.error(f"Heartbeat loop error for agent {agent_id}: {e}")
            await asyncio.sleep(60)  # Wait before retry


def start_heartbeat_runner(
    agents: dict[str, dict[str, Any]],
    execute_fn: Callable[[str, str], Any],
    is_busy_fn: Callable[[str], bool] | None = None,
) -> Callable:
    """
    Start heartbeat runners for all configured agents.
    
    Args:
        agents: Dict of agent_id -> agent_config
        execute_fn: Async function(agent_id, prompt) to execute heartbeat
        is_busy_fn: Function(agent_id) -> bool to check if agent is busy
    
    Returns:
        stop function to cancel all heartbeat tasks
    """
    for agent_id, agent_config in agents.items():
        if is_heartbeat_enabled_for_agent(agent_config):
            task = asyncio.create_task(
                _heartbeat_loop(agent_id, agent_config, execute_fn, is_busy_fn)
            )
            _running_tasks[agent_id] = task
            logger.info(f"Started heartbeat for agent: {agent_id}")
    
    def stop():
        for agent_id, task in _running_tasks.items():
            task.cancel()
            logger.info(f"Stopped heartbeat for agent: {agent_id}")
        _running_tasks.clear()
    
    return stop
