"""
Tests for tool result formatting
"""

import pytest

from openclaw.agents.formatting import FormatMode, ToolFormatter


class TestFormatMode:
    """Test FormatMode enum"""

    def test_mode_values(self):
        """Test enum values"""
        assert FormatMode.MARKDOWN == "markdown"
        assert FormatMode.PLAIN == "plain"


class TestToolFormatter:
    """Test ToolFormatter class"""

    def test_formatter_creation(self):
        """Test creating formatter"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)
        assert formatter.mode == FormatMode.MARKDOWN

    def test_format_tool_use_markdown(self):
        """Test formatting tool use in markdown"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)

        result = formatter.format_tool_use("bash", {"command": "ls -la"})

        assert "### 🔧 Tool: bash" in result
        assert "Arguments:" in result
        assert "ls -la" in result
        assert "```" in result

    def test_format_tool_use_plain(self):
        """Test formatting tool use in plain text"""
        formatter = ToolFormatter(FormatMode.PLAIN)

        result = formatter.format_tool_use("bash", {"command": "pwd"})

        assert "[Tool: bash]" in result
        assert "pwd" in result
        assert "```" not in result  # No markdown

    def test_format_tool_result_markdown_success(self):
        """Test formatting successful result in markdown"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)

        result = formatter.format_tool_result("bash", "/home/user", success=True)

        assert "✅" in result
        assert "bash" in result
        assert "/home/user" in result

    def test_format_tool_result_markdown_error(self):
        """Test formatting error result in markdown"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)

        result = formatter.format_tool_result("bash", "Command failed", success=False)

        assert "❌" in result
        assert "bash" in result
        assert "Command failed" in result

    def test_format_tool_result_plain(self):
        """Test formatting result in plain text"""
        formatter = ToolFormatter(FormatMode.PLAIN)

        result = formatter.format_tool_result("read_file", "File contents here", success=True)

        assert "[SUCCESS]" in result
        assert "read_file" in result
        assert "File contents here" in result

    def test_format_dict_result(self):
        """Test formatting dictionary result"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)

        result = formatter.format_tool_result(
            "api_call", {"status": "ok", "data": "value"}, success=True
        )

        assert "```json" in result
        assert "status" in result
        assert "ok" in result

    def test_truncate_long_result(self):
        """Test truncation of long results"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)

        long_text = "x" * 10000
        result = formatter.format_tool_result("tool", long_text, truncate=True)

        assert len(result) < len(long_text)
        assert "truncated" in result

    def test_no_truncate(self):
        """Test no truncation when disabled"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)

        long_text = "y" * 1000
        result = formatter.format_tool_result("tool", long_text, truncate=False)

        assert long_text in result

    def test_code_detection(self):
        """Test code detection and highlighting"""
        formatter = ToolFormatter(FormatMode.MARKDOWN)

        code = "def hello():\n    print('world')"
        result = formatter.format_tool_result("read_file", code, success=True)

        assert "```python" in result
        assert code in result

    def test_detect_language(self):
        """Test language detection"""
        formatter = ToolFormatter()

        assert formatter._detect_language("def test():\n    pass") == "python"
        assert formatter._detect_language("function test() {}") == "javascript"
        assert formatter._detect_language("public class Test {}") == "java"
