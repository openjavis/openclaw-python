"""TUI type definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TUIOptions:
    """Options for TUI."""

    agent_id: str = "default"
    session_key: str | None = None
    workspace_dir: str | None = None
    config_path: str | None = None
