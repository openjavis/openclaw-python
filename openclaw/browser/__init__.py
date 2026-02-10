"""Unified browser automation module

Consolidates browser functionality from:
- openclaw/agents/tools/browser.py
- openclaw/agents/tools/browser_control.py

Provides:
- Browser controller (Playwright-based)
- Sandbox bridge for isolated execution
- Chrome extension relay
- Profile management
"""

from .controller import BrowserController
from .profiles import BrowserProfile
from .tools.browser_tool import UnifiedBrowserTool

__all__ = [
    "BrowserController",
    "BrowserProfile",
    "UnifiedBrowserTool",
]
