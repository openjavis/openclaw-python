"""Backward-compatibility shim for openclaw.tui.tui_app.

The TUI has been rewritten using pi_tui (see tui.py).
This module re-exports the new classes under the old names so that
existing imports continue to work.
"""
from __future__ import annotations

from .tui import TUI as OpenClawTUI, TUIOptions, run_tui

__all__ = ["OpenClawTUI", "TUIOptions", "run_tui"]
