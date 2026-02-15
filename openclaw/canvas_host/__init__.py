"""
Canvas Host system for A2UI rendering.

Provides WebSocket-based canvas for displaying interactive UIs.
"""

from .server import CanvasHostServer
from .a2ui_protocol import A2UI_ACTION_KEYS, SurfaceUpdate, BeginRendering

__all__ = [
    "CanvasHostServer",
    "A2UI_ACTION_KEYS",
    "SurfaceUpdate",
    "BeginRendering",
]
