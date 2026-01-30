"""Canvas tool for visual workspace (A2UI)"""

import logging
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class CanvasTool(AgentTool):
    """Canvas/A2UI visual workspace control"""

    def __init__(self):
        super().__init__()
        self.name = "canvas"
        self.description = "Control the Canvas visual workspace for presenting UI, visualizations, and interactive content"
        self._canvas_active = False
        self._canvas_url = None

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "present",
                        "hide",
                        "navigate",
                        "eval",
                        "snapshot",
                        "a2ui_push",
                        "a2ui_reset",
                    ],
                    "description": "Canvas action to perform",
                },
                "url": {"type": "string", "description": "URL to present or navigate to"},
                "code": {"type": "string", "description": "JavaScript code to evaluate in canvas"},
                "data": {"type": "object", "description": "Data for A2UI push"},
                "output_path": {"type": "string", "description": "Path to save snapshot"},
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute canvas action"""
        action = params.get("action", "")

        if not action:
            return ToolResult(success=False, content="", error="action required")

        try:
            if action == "present":
                return await self._present(params)
            elif action == "hide":
                return await self._hide(params)
            elif action == "navigate":
                return await self._navigate(params)
            elif action == "eval":
                return await self._eval(params)
            elif action == "snapshot":
                return await self._snapshot(params)
            elif action == "a2ui_push":
                return await self._a2ui_push(params)
            elif action == "a2ui_reset":
                return await self._a2ui_reset(params)
            else:
                return ToolResult(success=False, content="", error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Canvas tool error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _present(self, params: dict[str, Any]) -> ToolResult:
        """Present canvas with URL"""
        url = params.get("url", "")

        if not url:
            return ToolResult(success=False, content="", error="url required")

        self._canvas_active = True
        self._canvas_url = url

        logger.info(f"Canvas presented: {url}")

        return ToolResult(
            success=True,
            content=f"Canvas presented with {url}",
            metadata={"active": True, "url": url},
        )

    async def _hide(self, params: dict[str, Any]) -> ToolResult:
        """Hide canvas"""
        self._canvas_active = False
        self._canvas_url = None

        return ToolResult(success=True, content="Canvas hidden")

    async def _navigate(self, params: dict[str, Any]) -> ToolResult:
        """Navigate canvas to URL"""
        url = params.get("url", "")

        if not url:
            return ToolResult(success=False, content="", error="url required")

        if not self._canvas_active:
            return ToolResult(
                success=False, content="", error="Canvas not active. Use action='present' first."
            )

        self._canvas_url = url

        return ToolResult(success=True, content=f"Canvas navigated to {url}")

    async def _eval(self, params: dict[str, Any]) -> ToolResult:
        """Evaluate JavaScript in canvas"""
        code = params.get("code", "")

        if not code:
            return ToolResult(success=False, content="", error="code required")

        if not self._canvas_active:
            return ToolResult(success=False, content="", error="Canvas not active")

        # This would require browser automation or canvas server
        logger.warning("Canvas eval requires canvas server integration")

        return ToolResult(
            success=False,
            content="",
            error="Canvas eval not fully implemented - requires canvas server",
        )

    async def _snapshot(self, params: dict[str, Any]) -> ToolResult:
        """Take canvas snapshot"""
        params.get("output_path", "canvas_snapshot.png")

        if not self._canvas_active:
            return ToolResult(success=False, content="", error="Canvas not active")

        logger.warning("Canvas snapshot requires canvas server")

        return ToolResult(
            success=False,
            content="",
            error="Canvas snapshot not fully implemented - requires canvas server",
        )

    async def _a2ui_push(self, params: dict[str, Any]) -> ToolResult:
        """Push data to A2UI"""
        data = params.get("data", {})

        if not data:
            return ToolResult(success=False, content="", error="data required")

        logger.info(f"A2UI push: {data}")

        return ToolResult(
            success=True, content="A2UI data pushed (placeholder)", metadata={"data": data}
        )

    async def _a2ui_reset(self, params: dict[str, Any]) -> ToolResult:
        """Reset A2UI state"""
        return ToolResult(success=True, content="A2UI reset")


# Note: Full Canvas/A2UI implementation requires:
# 1. Canvas server (HTTP server serving canvas UI)
# 2. WebSocket communication for live updates
# 3. A2UI framework integration (agent-to-UI protocol)
# 4. Browser automation for snapshots/eval
#
# The TypeScript version has a dedicated canvas server at port 18793
# serving /__openclaw__/canvas/ with full A2UI support.
