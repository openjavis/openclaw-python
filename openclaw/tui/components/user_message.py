"""User message component.

Renders user turns in the chat log.
Mirrors TypeScript src/tui/components/user-message.ts.
"""
from __future__ import annotations

_ANSI_BOLD = "\033[1m"
_ANSI_BLUE = "\033[34m"
_ANSI_RESET = "\033[0m"


class UserMessageComponent:
    """Renders a single user message."""

    def __init__(self, text: str, width: int = 80) -> None:
        self.text = text
        self.width = width

    def render_lines(self) -> list[str]:
        """Return terminal lines for this user message."""
        lines: list[str] = []
        try:
            from pi_tui import wrap_text_with_ansi
            wrapped = wrap_text_with_ansi(self.text, self.width - 6)
        except Exception:
            wrapped = self.text.splitlines() or [""]

        prefix = _ANSI_BLUE + _ANSI_BOLD + "You: " + _ANSI_RESET
        pad = " " * 5
        for i, line in enumerate(wrapped):
            lines.append((prefix if i == 0 else pad) + line)
        return lines or [prefix]
