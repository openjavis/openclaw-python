"""
Session Status Tool - provides current time and session information

Aligned with openclaw/src/agents/tools/session-*.ts
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC
from typing import Any

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

from ..tools.base import SimpleTool, AgentToolResult
from ..types import TextContent

logger = logging.getLogger(__name__)


async def session_status_tool_execute(
    tool_call_id: str,
    params: dict,
    signal: Any | None,
    on_update: Any | None
) -> AgentToolResult:
    """
    Get current session status including time information
    
    Args:
        tool_call_id: Tool call identifier
        params: Parameters dict with optional 'timezone' key
        signal: Cancellation signal (unused)
        on_update: Update callback (unused)
        
    Returns:
        Session status with current time
    """
    # Extract timezone from params
    timezone = params.get("timezone", "UTC") if params else "UTC"
    
    try:
        # Get current time in specified timezone
        if HAS_PYTZ:
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone: {timezone}, using UTC")
                now = datetime.now(UTC)
        else:
            # Fallback to UTC if pytz not available
            logger.warning("pytz not installed, using UTC timezone")
            now = datetime.now(UTC)
        
        # Format time information
        status_text = f"""# Session Status

**Current Time**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**Timezone**: {timezone}
**Date**: {now.strftime('%Y-%m-%d')}
**Time**: {now.strftime('%H:%M:%S')}
**Day of Week**: {now.strftime('%A')}
**Year**: {now.year}
**Month**: {now.strftime('%B')}
**ISO Timestamp**: {now.isoformat()}

**Note**: This is the ACTUAL CURRENT TIME. Use this information for time-aware operations."""
        
        return AgentToolResult(
            content=[TextContent(text=status_text)],
            details={
                "timestamp": now.isoformat(),
                "timezone": timezone,
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M:%S'),
                "day_of_week": now.strftime('%A'),
                "year": now.year,
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return AgentToolResult(
            content=[TextContent(text=f"Error getting session status: {str(e)}")],
            details={"error": str(e)}
        )


# Create the session_status tool definition
SESSION_STATUS_TOOL = SimpleTool(
    name="session_status",
    label="Session Status",
    description="Get current session status including current date and time. Use this tool when you need to know the current time or date.",
    parameters={
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone (e.g., 'America/New_York', 'Asia/Shanghai', 'UTC'). Defaults to UTC.",
                "default": "UTC"
            }
        },
        "required": []
    },
    execute_fn=session_status_tool_execute,
)


def get_current_time_text(timezone: str = "UTC") -> str:
    """
    Get current time as formatted text
    
    Helper function for quick time formatting
    
    Args:
        timezone: Timezone string
        
    Returns:
        Formatted current time string
    """
    if HAS_PYTZ:
        try:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
        except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
            now = datetime.now(UTC)
    else:
        now = datetime.now(UTC)
    
    return f"{now.strftime('%Y-%m-%d %H:%M:%S')} {timezone}"


__all__ = [
    "SESSION_STATUS_TOOL",
    "session_status_tool_execute",
    "get_current_time_text",
]
