"""
Agent module for ClawdBot
"""

from .agent import Agent
from .queues import AgentSession  # Simple queue-based session for Agent class
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
from .tool_loop import ToolLoopOrchestrator

__all__ = [
    # Core
    "Agent",
    # Runtime
    "AgentRuntime",
    "AgentEvent",
    "AgentSession",  # New pi-ai style session
    "ToolLoopOrchestrator",  # Tool loop orchestrator
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
