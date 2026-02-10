"""Schedule computation matching TypeScript openclaw/src/cron/schedule.ts"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from croniter import croniter

from .types import AtSchedule, CronSchedule, CronScheduleType, EverySchedule

logger = logging.getLogger(__name__)


def compute_next_run(schedule: CronScheduleType, now_ms: int | None = None) -> int | None:
    """
    Compute next run time for schedule
    
    Args:
        schedule: Schedule configuration
        now_ms: Current time in milliseconds (default: now)
        
    Returns:
        Next run time in milliseconds, or None if schedule is invalid
    """
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    try:
        if isinstance(schedule, AtSchedule):
            return _compute_at_schedule(schedule, now_ms)
        elif isinstance(schedule, EverySchedule):
            return _compute_every_schedule(schedule, now_ms)
        elif isinstance(schedule, CronSchedule):
            return _compute_cron_schedule(schedule, now_ms)
        else:
            logger.error(f"Unknown schedule type: {type(schedule)}")
            return None
    except Exception as e:
        logger.error(f"Error computing next run: {e}", exc_info=True)
        return None


def _compute_at_schedule(schedule: AtSchedule, now_ms: int) -> int | None:
    """
    Compute next run for 'at' schedule (one-time timestamp)
    
    Args:
        schedule: At schedule
        now_ms: Current time in milliseconds
        
    Returns:
        Timestamp in milliseconds if in future, None otherwise
    """
    try:
        # Parse ISO-8601 timestamp
        dt = datetime.fromisoformat(schedule.timestamp.replace('Z', '+00:00'))
        run_ms = int(dt.timestamp() * 1000)
        
        # Only return if in future
        if run_ms > now_ms:
            return run_ms
        else:
            logger.debug(f"At schedule {schedule.timestamp} is in the past")
            return None
            
    except Exception as e:
        logger.error(f"Error parsing at schedule timestamp: {e}")
        return None


def _compute_every_schedule(schedule: EverySchedule, now_ms: int) -> int | None:
    """
    Compute next run for 'every' schedule (interval-based)
    
    Args:
        schedule: Every schedule
        now_ms: Current time in milliseconds
        
    Returns:
        Next run timestamp in milliseconds
    """
    interval_ms = schedule.interval_ms
    
    if interval_ms <= 0:
        logger.error(f"Invalid interval: {interval_ms}")
        return None
    
    # If anchor is provided, use it as base
    if schedule.anchor:
        try:
            anchor_dt = datetime.fromisoformat(schedule.anchor.replace('Z', '+00:00'))
            anchor_ms = int(anchor_dt.timestamp() * 1000)
            
            # Calculate how many intervals have passed since anchor
            elapsed_ms = now_ms - anchor_ms
            
            if elapsed_ms < 0:
                # Anchor is in future, use it as next run
                return anchor_ms
            
            # Calculate next interval after now
            intervals_passed = elapsed_ms // interval_ms
            next_run_ms = anchor_ms + (intervals_passed + 1) * interval_ms
            
            return next_run_ms
            
        except Exception as e:
            logger.error(f"Error parsing anchor timestamp: {e}")
            # Fall through to use now as base
    
    # No anchor or anchor parsing failed - use now as base
    return now_ms + interval_ms


def _compute_cron_schedule(schedule: CronSchedule, now_ms: int) -> int | None:
    """
    Compute next run for 'cron' schedule (cron expression)
    
    Args:
        schedule: Cron schedule
        now_ms: Current time in milliseconds
        
    Returns:
        Next run timestamp in milliseconds
    """
    try:
        # Convert now_ms to datetime
        now_dt = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc)
        
        # Create croniter instance
        cron = croniter(schedule.expression, now_dt)
        
        # Get next occurrence
        next_dt = cron.get_next(datetime)
        next_ms = int(next_dt.timestamp() * 1000)
        
        return next_ms
        
    except Exception as e:
        logger.error(f"Error computing cron schedule: {e}")
        return None


def format_next_run(next_run_ms: int | None) -> str:
    """
    Format next run time as human-readable string
    
    Args:
        next_run_ms: Next run time in milliseconds
        
    Returns:
        Formatted string
    """
    if next_run_ms is None:
        return "Never"
    
    try:
        dt = datetime.fromtimestamp(next_run_ms / 1000, tz=timezone.utc)
        
        # Get time until run
        now = datetime.now(timezone.utc)
        delta = dt - now
        
        if delta.total_seconds() < 0:
            return f"{dt.isoformat()} (overdue)"
        elif delta.total_seconds() < 60:
            return f"in {int(delta.total_seconds())}s"
        elif delta.total_seconds() < 3600:
            return f"in {int(delta.total_seconds() / 60)}m"
        elif delta.total_seconds() < 86400:
            return f"in {int(delta.total_seconds() / 3600)}h"
        else:
            return f"in {int(delta.total_seconds() / 86400)}d"
            
    except Exception as e:
        logger.error(f"Error formatting next run: {e}")
        return "Unknown"


def is_due(next_run_ms: int | None, now_ms: int | None = None) -> bool:
    """
    Check if job is due to run
    
    Args:
        next_run_ms: Next run time in milliseconds
        now_ms: Current time in milliseconds (default: now)
        
    Returns:
        True if job is due
    """
    if next_run_ms is None:
        return False
    
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    return next_run_ms <= now_ms
