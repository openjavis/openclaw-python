"""Global logging state."""

from __future__ import annotations

from dataclasses import dataclass

from .levels import LogLevel


@dataclass
class LoggingState:
    """Global logging state."""

    console_level: LogLevel = LogLevel.INFO
    console_style: str = "pretty"  # pretty, compact, json
    console_timestamp_prefix: bool = False
    force_console_to_stderr: bool = False
    raw_console: any | None = None
    file_logging_enabled: bool = True
    file_log_path: str | None = None


# Global state instance
_LOGGING_STATE = LoggingState()


def get_logging_state() -> LoggingState:
    """Get global logging state.

    Returns:
        Current logging state
    """
    return _LOGGING_STATE


def set_logging_state(**kwargs) -> None:
    """Update global logging state.

    Args:
        **kwargs: State fields to update
    """
    global _LOGGING_STATE

    for key, value in kwargs.items():
        if hasattr(_LOGGING_STATE, key):
            setattr(_LOGGING_STATE, key, value)


def get_console_settings() -> dict:
    """Get console logging settings.

    Returns:
        Dictionary with console settings
    """
    return {"level": _LOGGING_STATE.console_level, "style": _LOGGING_STATE.console_style}
