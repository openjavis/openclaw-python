"""Subsystem-based structured logging.

Aligned with TypeScript src/logging/subsystem.ts
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Protocol

from .formatters import format_console_line
from .levels import LogLevel, should_log
from .state import get_console_settings, get_logging_state


class SubsystemLogger(Protocol):
    """Protocol for subsystem logger."""

    subsystem: str

    def trace(self, message: str, meta: dict | None = None) -> None: ...
    def debug(self, message: str, meta: dict | None = None) -> None: ...
    def info(self, message: str, meta: dict | None = None) -> None: ...
    def warn(self, message: str, meta: dict | None = None) -> None: ...
    def error(self, message: str, meta: dict | None = None) -> None: ...
    def fatal(self, message: str, meta: dict | None = None) -> None: ...
    def raw(self, message: str) -> None: ...
    def child(self, name: str) -> SubsystemLogger: ...


class SubsystemLoggerImpl:
    """Implementation of subsystem logger.

    Provides structured, colorized logging with subsystem tagging.
    """

    def __init__(self, subsystem: str):
        """Initialize logger for subsystem.

        Args:
            subsystem: Subsystem name (e.g., "gateway/auth")
        """
        self.subsystem = subsystem
        self._file_logger: logging.Logger | None = None

    def _get_file_logger(self) -> logging.Logger:
        """Get or create file logger.

        Returns:
            Standard library logger for file logging
        """
        if self._file_logger:
            return self._file_logger

        logger = logging.getLogger(f"openclaw.{self.subsystem}")
        logger.setLevel(logging.DEBUG)

        # Add file handler if enabled
        state = get_logging_state()
        if state.file_logging_enabled and state.file_log_path:
            log_path = Path(state.file_log_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            handler = logging.FileHandler(log_path)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        self._file_logger = logger
        return self._file_logger

    def _emit(self, level: LogLevel, message: str, meta: dict | None = None) -> None:
        """Emit log message.

        Args:
            level: Log level
            message: Log message
            meta: Optional metadata
        """
        state = get_logging_state()
        console_settings = get_console_settings()

        # Log to file
        if state.file_logging_enabled:
            file_logger = self._get_file_logger()

            # Map to standard library levels
            if level == LogLevel.TRACE or level == LogLevel.DEBUG:
                file_logger.debug(message)
            elif level == LogLevel.INFO:
                file_logger.info(message)
            elif level == LogLevel.WARN:
                file_logger.warning(message)
            elif level in (LogLevel.ERROR, LogLevel.FATAL):
                file_logger.error(message)

        # Check if should log to console
        if not should_log(level, console_settings["level"]):
            return

        # Format and write to console
        formatted = format_console_line(
            level=level,
            subsystem=self.subsystem,
            message=message,
            style=console_settings["style"],
            meta=meta,
        )

        # Write to appropriate stream
        stream = (
            sys.stderr if state.force_console_to_stderr or level >= LogLevel.ERROR else sys.stdout
        )

        if state.raw_console:
            # Use custom console if provided
            print(formatted, file=stream)
        else:
            print(formatted, file=stream)

    def trace(self, message: str, meta: dict | None = None) -> None:
        """Log trace message."""
        self._emit(LogLevel.TRACE, message, meta)

    def debug(self, message: str, meta: dict | None = None) -> None:
        """Log debug message."""
        self._emit(LogLevel.DEBUG, message, meta)

    def info(self, message: str, meta: dict | None = None) -> None:
        """Log info message."""
        self._emit(LogLevel.INFO, message, meta)

    def warn(self, message: str, meta: dict | None = None) -> None:
        """Log warning message."""
        self._emit(LogLevel.WARN, message, meta)

    def error(self, message: str, meta: dict | None = None) -> None:
        """Log error message."""
        self._emit(LogLevel.ERROR, message, meta)

    def fatal(self, message: str, meta: dict | None = None) -> None:
        """Log fatal message."""
        self._emit(LogLevel.FATAL, message, meta)

    def raw(self, message: str) -> None:
        """Log raw message without formatting.

        Args:
            message: Raw message text
        """
        state = get_logging_state()
        stream = sys.stderr if state.force_console_to_stderr else sys.stdout
        print(message, file=stream)

    def child(self, name: str) -> SubsystemLogger:
        """Create child logger with nested subsystem name.

        Args:
            name: Child subsystem name

        Returns:
            New SubsystemLogger for child subsystem
        """
        child_subsystem = f"{self.subsystem}/{name}"
        return create_subsystem_logger(child_subsystem)


def create_subsystem_logger(subsystem: str) -> SubsystemLogger:
    """Create a subsystem logger.

    Args:
        subsystem: Subsystem name (e.g., "gateway/auth")

    Returns:
        SubsystemLogger instance
    """
    return SubsystemLoggerImpl(subsystem)


# Example usage:
# logger = create_subsystem_logger("gateway/auth")
# logger.info("User authenticated", {"userId": "123"})
# logger.error("Authentication failed")
