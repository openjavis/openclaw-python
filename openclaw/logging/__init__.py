"""Structured logging system for OpenClaw.

Aligned with TypeScript src/logging/subsystem.ts
"""

from __future__ import annotations

from .levels import MAX_LEVEL, MIN_LEVEL, LogLevel
from .state import get_logging_state, set_logging_state
from .subsystem import SubsystemLogger, create_subsystem_logger

__all__ = [
    "create_subsystem_logger",
    "SubsystemLogger",
    "LogLevel",
    "MIN_LEVEL",
    "MAX_LEVEL",
    "get_logging_state",
    "set_logging_state",
]
