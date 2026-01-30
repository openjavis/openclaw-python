"""
Tool result formatting
"""

from enum import Enum
from typing import Any


class FormatMode(str, Enum):
    """Format mode for tool results"""

    MARKDOWN = "markdown"  # Rich markdown format
    PLAIN = "plain"  # Plain text format


class ToolFormatter:
    """
    Format tool results for different channels

    Features:
    - Markdown formatting for web/telegram
    - Plain text for SMS/simple channels
    - Code block highlighting
    - Truncation for long outputs
    """

    MAX_OUTPUT_LENGTH = 4000  # Max characters in output

    def __init__(self, mode: FormatMode = FormatMode.MARKDOWN):
        """
        Initialize formatter

        Args:
            mode: Format mode
        """
        self.mode = mode

    def format_tool_use(
        self, tool_name: str, arguments: dict[str, Any], truncate: bool = True
    ) -> str:
        """
        Format tool invocation

        Args:
            tool_name: Tool name
            arguments: Tool arguments
            truncate: Whether to truncate long arguments

        Returns:
            Formatted string
        """
        if self.mode == FormatMode.MARKDOWN:
            return self._format_tool_use_markdown(tool_name, arguments, truncate)
        else:
            return self._format_tool_use_plain(tool_name, arguments, truncate)

    def format_tool_result(
        self, tool_name: str, result: str | dict, success: bool = True, truncate: bool = True
    ) -> str:
        """
        Format tool result

        Args:
            tool_name: Tool name
            result: Tool result (string or dict)
            success: Whether tool succeeded
            truncate: Whether to truncate long results

        Returns:
            Formatted string
        """
        if self.mode == FormatMode.MARKDOWN:
            return self._format_tool_result_markdown(tool_name, result, success, truncate)
        else:
            return self._format_tool_result_plain(tool_name, result, success, truncate)

    def _format_tool_use_markdown(
        self, tool_name: str, arguments: dict[str, Any], truncate: bool
    ) -> str:
        """Format tool use in markdown"""
        result = f"### 🔧 Tool: {tool_name}\n\n"

        if arguments:
            result += "**Arguments:**\n```json\n"
            args_str = self._format_dict(arguments)
            if truncate and len(args_str) > 500:
                args_str = args_str[:500] + "..."
            result += args_str + "\n```\n"

        return result

    def _format_tool_use_plain(
        self, tool_name: str, arguments: dict[str, Any], truncate: bool
    ) -> str:
        """Format tool use in plain text"""
        result = f"[Tool: {tool_name}]\n"

        if arguments:
            args_str = self._format_dict(arguments)
            if truncate and len(args_str) > 200:
                args_str = args_str[:200] + "..."
            result += f"Arguments: {args_str}\n"

        return result

    def _format_tool_result_markdown(
        self, tool_name: str, result: str | dict, success: bool, truncate: bool
    ) -> str:
        """Format tool result in markdown"""
        status = "✅" if success else "❌"
        formatted = f"### {status} Result: {tool_name}\n\n"

        if isinstance(result, dict):
            formatted += "```json\n" + self._format_dict(result) + "\n```\n"
        else:
            result_str = str(result)
            if truncate and len(result_str) > self.MAX_OUTPUT_LENGTH:
                result_str = result_str[: self.MAX_OUTPUT_LENGTH] + "\n... (truncated)"

            # Try to detect code and wrap in code block
            if self._looks_like_code(result_str):
                lang = self._detect_language(result_str)
                formatted += f"```{lang}\n{result_str}\n```\n"
            else:
                formatted += result_str + "\n"

        return formatted

    def _format_tool_result_plain(
        self, tool_name: str, result: str | dict, success: bool, truncate: bool
    ) -> str:
        """Format tool result in plain text"""
        status = "[SUCCESS]" if success else "[ERROR]"
        formatted = f"{status} {tool_name}:\n"

        if isinstance(result, dict):
            formatted += self._format_dict(result) + "\n"
        else:
            result_str = str(result)
            if truncate and len(result_str) > self.MAX_OUTPUT_LENGTH:
                result_str = result_str[: self.MAX_OUTPUT_LENGTH] + "\n... (truncated)"
            formatted += result_str + "\n"

        return formatted

    def _format_dict(self, data: dict) -> str:
        """Format dictionary nicely"""
        import json

        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception:
            return str(data)

    def _looks_like_code(self, text: str) -> bool:
        """Detect if text looks like code"""
        code_indicators = [
            "def ",
            "class ",
            "import ",
            "function",
            "const ",
            "let ",
            "var ",
            "{",
            "}",
            "=>",
            "public ",
            "private ",
        ]
        return any(indicator in text for indicator in code_indicators)

    def _detect_language(self, text: str) -> str:
        """Detect programming language from code"""
        if "def " in text or "import " in text or "__init__" in text:
            return "python"
        elif "function" in text or "const " in text or "=>" in text:
            return "javascript"
        elif "public " in text or "private " in text or "class" in text:
            return "java"
        else:
            return ""
