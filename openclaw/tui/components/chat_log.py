"""Chat log component — scrollable history.

Renders the full conversation history using pi_tui primitives.
Mirrors TypeScript src/tui/components/chat-log.ts.
"""
from __future__ import annotations

from typing import Any


class ChatMessage:
    """A single rendered message in the chat log."""

    def __init__(self, role: str, content: str, timestamp: int = 0) -> None:
        self.role = role
        self.content = content
        self.timestamp = timestamp

    def render_lines(self, width: int = 80) -> list[str]:
        """Return list of terminal lines for this message."""
        from pi_tui import wrap_text_with_ansi

        prefix = "You: " if self.role == "user" else "  › "
        wrapped = wrap_text_with_ansi(self.content, width - len(prefix))
        lines = []
        for i, line in enumerate(wrapped):
            if i == 0:
                lines.append(prefix + line)
            else:
                lines.append(" " * len(prefix) + line)
        return lines or [prefix]


class ChatLog:
    """Scrollable chat history component.

    Stores a list of ChatMessage objects and renders them to terminal lines.
    Supports scroll offset for long conversations.
    """

    def __init__(self, width: int = 80, height: int = 20) -> None:
        self._messages: list[ChatMessage] = []
        self._width = width
        self._height = height
        self._scroll_offset = 0  # lines from bottom

    def add_message(self, role: str, content: str, timestamp: int = 0) -> None:
        """Append a message to the log."""
        self._messages.append(ChatMessage(role=role, content=content, timestamp=timestamp))
        self._scroll_offset = 0  # Reset scroll on new message

    def update_last_assistant(self, content: str) -> None:
        """Update the last assistant message in place (for streaming)."""
        for msg in reversed(self._messages):
            if msg.role == "assistant":
                msg.content = content
                return
        # No assistant message yet — create one
        self._messages.append(ChatMessage(role="assistant", content=content))

    def render(self) -> list[str]:
        """Render all lines from the log, cropped to height."""
        all_lines: list[str] = []
        for msg in self._messages:
            all_lines.extend(msg.render_lines(self._width))
            all_lines.append("")  # blank separator

        total = len(all_lines)
        if total <= self._height:
            return all_lines

        # Apply scroll
        visible_start = max(0, total - self._height - self._scroll_offset)
        return all_lines[visible_start : visible_start + self._height]

    def scroll_up(self, n: int = 3) -> None:
        self._scroll_offset = min(self._scroll_offset + n, self._max_scroll())

    def scroll_down(self, n: int = 3) -> None:
        self._scroll_offset = max(0, self._scroll_offset - n)

    def scroll_to_bottom(self) -> None:
        self._scroll_offset = 0

    def _max_scroll(self) -> int:
        total = sum(
            len(m.render_lines(self._width)) + 1 for m in self._messages
        )
        return max(0, total - self._height)

    def resize(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def clear(self) -> None:
        self._messages.clear()
        self._scroll_offset = 0
