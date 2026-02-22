"""Tool execution component.

Renders inline tool call progress/results.
Mirrors TypeScript src/tui/components/tool-execution.ts.
"""
from __future__ import annotations

_ANSI_CYAN = "\033[36m"
_ANSI_GREEN = "\033[32m"
_ANSI_RED = "\033[31m"
_ANSI_DIM = "\033[2m"
_ANSI_RESET = "\033[0m"


class ToolExecutionComponent:
    """Renders a single tool call with status and result."""

    def __init__(
        self,
        tool_name: str,
        tool_call_id: str,
        arguments: dict | None = None,
        result: str = "",
        success: bool = True,
        status: str = "running",
        width: int = 80,
    ) -> None:
        self.tool_name = tool_name
        self.tool_call_id = tool_call_id
        self.arguments = arguments or {}
        self.result = result
        self.success = success
        self.status = status  # "running" | "done" | "error"
        self.width = width

    def render_lines(self) -> list[str]:
        """Return terminal lines for this tool execution."""
        lines: list[str] = []

        if self.status == "running":
            icon = "○"
            color = _ANSI_CYAN
        elif self.status == "done" and self.success:
            icon = "✓"
            color = _ANSI_GREEN
        else:
            icon = "✗"
            color = _ANSI_RED

        # Header line
        lines.append(f"{color}{icon} {self.tool_name}{_ANSI_RESET}")

        # Arguments (compact)
        if self.arguments and self.status != "done":
            args_str = ", ".join(f"{k}={repr(v)[:30]}" for k, v in list(self.arguments.items())[:3])
            lines.append(_ANSI_DIM + "  (" + args_str + ")" + _ANSI_RESET)

        # Result (first 3 lines only)
        if self.result and self.status in ("done", "error"):
            result_lines = str(self.result).splitlines()
            for line in result_lines[:3]:
                lines.append(_ANSI_DIM + "  " + line[:self.width - 4] + _ANSI_RESET)
            if len(result_lines) > 3:
                lines.append(_ANSI_DIM + f"  … ({len(result_lines) - 3} more lines)" + _ANSI_RESET)

        return lines
