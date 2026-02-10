"""Setup wizard for OpenClaw.

Interactive configuration wizard for first-time setup.
"""

from __future__ import annotations

from .onboarding import run_onboarding
from .config import configure_agent, configure_channels
from .session import WizardSession, WizardStep, WizardStepType

__all__ = [
    "run_onboarding",
    "configure_agent",
    "configure_channels",
    "WizardSession",
    "WizardStep",
    "WizardStepType",
]
