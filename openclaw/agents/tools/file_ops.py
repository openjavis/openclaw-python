"""File operation tools"""

import logging
from pathlib import Path
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class ReadFileTool(AgentTool):
    """Read file contents"""

    def __init__(self):
        super().__init__()
        self.name = "read_file"
        self.description = "Read contents of a file"

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Path to the file to read"}},
            "required": ["path"],
        }

    async def _execute_impl(self, params: dict[str, Any]) -> ToolResult:
        """Read file"""
        file_path = params.get("path", "")

        if not file_path:
            return ToolResult(success=False, content="", error="No path provided")

        try:
            path = Path(file_path).expanduser()

            if not path.exists():
                return ToolResult(success=False, content="", error=f"File not found: {file_path}")

            if not path.is_file():
                return ToolResult(success=False, content="", error=f"Not a file: {file_path}")

            content = path.read_text(encoding="utf-8")
            return ToolResult(success=True, content=content)

        except Exception as e:
            logger.error(f"Read file error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class WriteFileTool(AgentTool):
    """Write file contents"""

    def __init__(self):
        super().__init__()
        self.name = "write_file"
        self.description = "Write contents to a file (creates or overwrites)"

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write to the file"},
            },
            "required": ["path", "content"],
        }

    async def _execute_impl(self, params: dict[str, Any]) -> ToolResult:
        """Write file"""
        file_path = params.get("path", "")
        content = params.get("content", "")

        if not file_path:
            return ToolResult(success=False, content="", error="No path provided")

        try:
            path = Path(file_path).expanduser()

            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            path.write_text(content, encoding="utf-8")

            return ToolResult(success=True, content=f"Wrote {len(content)} bytes to {file_path}")

        except Exception as e:
            logger.error(f"Write file error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class EditFileTool(AgentTool):
    """Edit file with search/replace"""

    def __init__(self):
        super().__init__()
        self.name = "edit_file"
        self.description = "Edit a file by searching and replacing text"

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to edit"},
                "old_text": {"type": "string", "description": "Text to search for"},
                "new_text": {"type": "string", "description": "Text to replace with"},
            },
            "required": ["path", "old_text", "new_text"],
        }

    async def _execute_impl(self, params: dict[str, Any]) -> ToolResult:
        """Edit file"""
        file_path = params.get("path", "")
        old_text = params.get("old_text", "")
        new_text = params.get("new_text", "")

        if not file_path:
            return ToolResult(success=False, content="", error="No path provided")

        try:
            path = Path(file_path).expanduser()

            if not path.exists():
                return ToolResult(success=False, content="", error=f"File not found: {file_path}")

            # Read file
            content = path.read_text(encoding="utf-8")

            # Check if old_text exists
            if old_text not in content:
                return ToolResult(
                    success=False, content="", error=f"Text not found in file: {old_text[:50]}..."
                )

            # Replace
            new_content = content.replace(old_text, new_text, 1)

            # Write back
            path.write_text(new_content, encoding="utf-8")

            return ToolResult(success=True, content=f"Replaced 1 occurrence in {file_path}")

        except Exception as e:
            logger.error(f"Edit file error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))
