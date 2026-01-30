"""Bash execution tool"""

import asyncio
import logging
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class BashTool(AgentTool):
    """Execute bash commands"""

    def __init__(self):
        super().__init__()
        self.name = "bash"
        self.description = (
            "Execute bash commands in a shell. Use for system operations, running scripts, etc."
        )

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to execute"},
                "working_directory": {
                    "type": "string",
                    "description": "Optional working directory for the command",
                },
            },
            "required": ["command"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute bash command"""
        command = params.get("command", "")
        working_dir = params.get("working_directory")

        if not command:
            return ToolResult(success=False, content="", error="No command provided")

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
            except TimeoutError:
                process.kill()
                return ToolResult(
                    success=False, content="", error="Command timed out after 30 seconds"
                )

            # Decode output
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")

            # Combine output
            output = ""
            if stdout_text:
                output += stdout_text
            if stderr_text:
                if output:
                    output += "\n"
                output += stderr_text

            return ToolResult(
                success=process.returncode == 0,
                content=output,
                error=None if process.returncode == 0 else f"Exit code: {process.returncode}",
                metadata={"exitCode": process.returncode},
            )

        except Exception as e:
            logger.error(f"Bash tool error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))
