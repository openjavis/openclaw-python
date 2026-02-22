"""Stream assembler for the TUI.

Converts streaming deltas from the gateway into displayable text.
Mirrors TypeScript openclaw/src/tui/tui-stream-assembler.ts.

Responsibilities:
- Accumulate text deltas into full message text
- Handle thinking blocks (show/hide based on verboseLevel)
- Drop boundary tokens (e.g. </reply> and <reply> tags)
- Track tool call progress
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# Tags that should be stripped from displayed output
_BOUNDARY_TAGS_RE = re.compile(r"</?(?:reply|thinking|tool_use|function_calls?)[^>]*>", re.IGNORECASE)


@dataclass
class AssembledMessage:
    """Current accumulated state for a streaming response."""

    text: str = ""
    thinking: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    is_done: bool = False
    stop_reason: str = ""


class StreamAssembler:
    """Assembles chat streaming events into displayable state.

    Usage::

        asm = StreamAssembler(verbose=False)
        for event in gateway_events:
            if event.type == "delta":
                asm.on_delta(event.text)
            elif event.type == "final":
                asm.on_final(event.message)
        display(asm.current.text)
    """

    def __init__(self, verbose: bool = False) -> None:
        self._verbose = verbose
        self._runs: dict[str, AssembledMessage] = {}

    def get_or_create(self, run_id: str) -> AssembledMessage:
        if run_id not in self._runs:
            self._runs[run_id] = AssembledMessage()
        return self._runs[run_id]

    def on_delta(self, run_id: str, text: str) -> AssembledMessage:
        """Process a text delta. Returns updated state."""
        msg = self.get_or_create(run_id)

        # Route to thinking vs main text
        if "<thinking>" in text or msg.thinking and not msg.thinking.endswith("</thinking>"):
            msg.thinking += text
        else:
            # Strip boundary tags unless verbose
            clean = _BOUNDARY_TAGS_RE.sub("", text) if not self._verbose else text
            msg.text += clean

        return msg

    def on_tool_call(self, run_id: str, tool_name: str, tool_call_id: str, arguments: dict) -> AssembledMessage:
        """Record a tool call in progress."""
        msg = self.get_or_create(run_id)
        msg.tool_calls.append({
            "name": tool_name,
            "id": tool_call_id,
            "arguments": arguments,
            "status": "running",
        })
        return msg

    def on_tool_result(self, run_id: str, tool_call_id: str, result: str, success: bool = True) -> AssembledMessage:
        """Update tool call with its result."""
        msg = self.get_or_create(run_id)
        for tc in msg.tool_calls:
            if tc["id"] == tool_call_id:
                tc["result"] = result
                tc["status"] = "done" if success else "error"
                break
        return msg

    def on_final(self, run_id: str, message: dict | None, stop_reason: str = "stop") -> AssembledMessage:
        """Mark a run as complete and merge final message if provided."""
        msg = self.get_or_create(run_id)
        msg.is_done = True
        msg.stop_reason = stop_reason

        if message:
            content = message.get("content", [])
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    # If we have no text yet, use message content
                    if not msg.text:
                        msg.text = block.get("text", "")
                    break

        return msg

    def reset(self, run_id: str) -> None:
        """Clear assembled state for a run."""
        self._runs.pop(run_id, None)

    def get_display_text(self, run_id: str, show_thinking: bool = False) -> str:
        """Get the text to display for a run."""
        msg = self._runs.get(run_id)
        if not msg:
            return ""
        text = msg.text
        if show_thinking and msg.thinking:
            text = f"[thinking]\n{msg.thinking}\n[/thinking]\n\n{text}"
        return text
