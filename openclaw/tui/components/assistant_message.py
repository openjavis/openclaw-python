"""Assistant message component.

Renders assistant responses including:
- Main text (markdown-formatted)
- Thinking blocks (collapsible)
- Tool call blocks (inline)

Mirrors TypeScript src/tui/components/assistant-message.ts.
"""
from __future__ import annotations

import re
from typing import Any


_ANSI_BOLD = "\033[1m"
_ANSI_DIM = "\033[2m"
_ANSI_CYAN = "\033[36m"
_ANSI_RESET = "\033[0m"


class AssistantMessageComponent:
    """Renders a single assistant message with optional thinking and tool blocks."""

    def __init__(
        self,
        text: str = "",
        thinking: str = "",
        tool_calls: list[dict] | None = None,
        show_thinking: bool = False,
        width: int = 80,
    ) -> None:
        self.text = text
        self.thinking = thinking
        self.tool_calls = tool_calls or []
        self.show_thinking = show_thinking
        self.width = width

    def render_lines(self) -> list[str]:
        """Return list of terminal lines for this assistant message."""
        lines: list[str] = []

        # Thinking block
        if self.thinking and self.show_thinking:
            lines.append(_ANSI_DIM + "┌─ thinking " + "─" * (self.width - 13) + "┐" + _ANSI_RESET)
            for line in self.thinking.splitlines():
                lines.append(_ANSI_DIM + "│ " + line + _ANSI_RESET)
            lines.append(_ANSI_DIM + "└" + "─" * (self.width - 2) + "┘" + _ANSI_RESET)

        # Tool call blocks
        for tc in self.tool_calls:
            name = tc.get("name", "tool")
            status = tc.get("status", "running")
            status_icon = "●" if status == "running" else ("✓" if status == "done" else "✗")
            lines.append(
                f"{_ANSI_CYAN}{status_icon} {name}{_ANSI_RESET}"
            )
            result = tc.get("result", "")
            if result and status != "running":
                for rline in str(result).splitlines()[:5]:  # Cap at 5 lines
                    lines.append(_ANSI_DIM + "  " + rline + _ANSI_RESET)

        # Main text
        try:
            from pi_tui import wrap_text_with_ansi
            wrapped = wrap_text_with_ansi(self.text, self.width - 4)
            for line in wrapped:
                lines.append("  " + line)
        except Exception:
            for line in self.text.splitlines():
                lines.append("  " + line)

        return lines or ["  "]
