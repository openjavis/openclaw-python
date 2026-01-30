"""
ClawdBot - Personal AI Assistant Platform

A Python implementation of the ClawdBot personal AI assistant platform.

Example usage:
    from openclaw.agents import AgentRuntime, Session
    from pathlib import Path

    runtime = AgentRuntime()
    session = Session("my-session", Path("./workspace"))

    async for event in runtime.run_turn(session, "Hello!"):
        if event.type == "assistant":
            print(event.data.get("delta", {}).get("text", ""))
"""

__version__ = "0.3.3"
__author__ = "ClawdBot Contributors"

from .agents import AgentRuntime, Session, SessionManager
from .config import Settings, get_settings
from .monitoring import get_health_check, get_metrics, setup_logging

__all__ = [
    "__version__",
    "AgentRuntime",
    "Session",
    "SessionManager",
    "get_settings",
    "Settings",
    "get_health_check",
    "get_metrics",
    "setup_logging",
]
