"""Setup wizard for OpenClaw.

Interactive configuration wizard for first-time setup.
"""

from __future__ import annotations

from .config import configure_agent, configure_channels
from .onboarding import run_onboarding

__all__ = [
    "run_onboarding",
    "configure_agent",
    "configure_channels",
]
