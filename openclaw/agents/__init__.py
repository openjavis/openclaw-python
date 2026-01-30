"""
Agent module for ClawdBot
"""

from .context import ContextManager, ContextWindow
from .errors import (
    AgentError,
    AuthenticationError,
    ContextOverflowError,
    ErrorRecovery,
    NetworkError,
    RateLimitError,
    TimeoutError,
    classify_error,
    format_error_message,
    is_retryable_error,
)
from .runtime import AgentEvent, AgentRuntime
from .session import Message, Session, SessionManager

__all__ = [
    # Runtime
    "AgentRuntime",
    "AgentEvent",
    # Session
    "Session",
    "SessionManager",
    "Message",
    # Context
    "ContextManager",
    "ContextWindow",
    # Errors
    "AgentError",
    "ContextOverflowError",
    "RateLimitError",
    "AuthenticationError",
    "NetworkError",
    "TimeoutError",
    "ErrorRecovery",
    "classify_error",
    "is_retryable_error",
    "format_error_message",
]
