"""Process management tool"""

import asyncio
import logging
from typing import Any

import psutil

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class ProcessTool(AgentTool):
    """Manage system processes"""

    def __init__(self):
        super().__init__()
        self.name = "process"
        self.description = "Manage and monitor system processes"
        self._tracked_processes: dict[str, asyncio.subprocess.Process] = {}

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "status", "list", "kill", "wait"],
                    "description": "Process action",
                },
                "command": {"type": "string", "description": "Command to execute (for start)"},
                "process_id": {"type": "string", "description": "Process identifier"},
                "pid": {"type": "integer", "description": "System process ID (for kill/status)"},
                "background": {
                    "type": "boolean",
                    "description": "Run in background",
                    "default": True,
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for the command",
                },
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute process action"""
        action = params.get("action", "")

        if not action:
            return ToolResult(success=False, content="", error="action required")

        try:
            if action == "start":
                return await self._start_process(params)
            elif action == "stop":
                return await self._stop_process(params)
            elif action == "status":
                return await self._process_status(params)
            elif action == "list":
                return await self._list_processes(params)
            elif action == "kill":
                return await self._kill_process(params)
            elif action == "wait":
                return await self._wait_process(params)
            else:
                return ToolResult(success=False, content="", error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Process tool error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))

    async def _start_process(self, params: dict[str, Any]) -> ToolResult:
        """Start a process"""
        command = params.get("command", "")
        process_id = params.get("process_id") or f"proc-{len(self._tracked_processes)}"
        background = params.get("background", True)
        working_dir = params.get("working_directory")

        if not command:
            return ToolResult(success=False, content="", error="command required")

        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=working_dir
        )

        # Track process
        self._tracked_processes[process_id] = process

        if not background:
            # Wait for completion
            stdout, stderr = await process.communicate()

            output = ""
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                if output:
                    output += "\n"
                output += stderr.decode("utf-8", errors="replace")

            # Remove from tracking
            del self._tracked_processes[process_id]

            return ToolResult(
                success=process.returncode == 0,
                content=output,
                metadata={
                    "process_id": process_id,
                    "exit_code": process.returncode,
                    "pid": process.pid,
                },
            )
        else:
            # Return immediately
            return ToolResult(
                success=True,
                content=f"Started process '{process_id}' (PID: {process.pid})",
                metadata={"process_id": process_id, "pid": process.pid, "background": True},
            )

    async def _stop_process(self, params: dict[str, Any]) -> ToolResult:
        """Stop a process gracefully"""
        process_id = params.get("process_id", "")

        if not process_id:
            return ToolResult(success=False, content="", error="process_id required")

        if process_id not in self._tracked_processes:
            return ToolResult(success=False, content="", error=f"Process '{process_id}' not found")

        process = self._tracked_processes[process_id]

        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except TimeoutError:
            process.kill()
            await process.wait()

        del self._tracked_processes[process_id]

        return ToolResult(success=True, content=f"Stopped process '{process_id}'")

    async def _process_status(self, params: dict[str, Any]) -> ToolResult:
        """Get process status"""
        process_id = params.get("process_id")
        pid = params.get("pid")

        if process_id:
            if process_id not in self._tracked_processes:
                return ToolResult(
                    success=False, content="", error=f"Process '{process_id}' not found"
                )

            process = self._tracked_processes[process_id]
            return_code = process.returncode

            if return_code is None:
                status = "running"
            else:
                status = f"exited with code {return_code}"

            return ToolResult(
                success=True,
                content=f"Process '{process_id}': {status}",
                metadata={
                    "process_id": process_id,
                    "pid": process.pid,
                    "status": status,
                    "return_code": return_code,
                },
            )

        elif pid:
            try:
                proc = psutil.Process(pid)
                info = {
                    "pid": pid,
                    "name": proc.name(),
                    "status": proc.status(),
                    "cpu_percent": proc.cpu_percent(),
                    "memory_percent": proc.memory_percent(),
                    "create_time": proc.create_time(),
                }

                output = f"Process {pid} ({info['name']}):\n"
                output += f"  Status: {info['status']}\n"
                output += f"  CPU: {info['cpu_percent']}%\n"
                output += f"  Memory: {info['memory_percent']:.1f}%\n"

                return ToolResult(success=True, content=output, metadata=info)

            except psutil.NoSuchProcess:
                return ToolResult(success=False, content="", error=f"Process {pid} not found")
            except ImportError:
                return ToolResult(
                    success=False,
                    content="",
                    error="psutil not installed. Install with: pip install psutil",
                )
        else:
            return ToolResult(success=False, content="", error="process_id or pid required")

    async def _list_processes(self, params: dict[str, Any]) -> ToolResult:
        """List tracked processes"""
        if not self._tracked_processes:
            return ToolResult(success=True, content="No tracked processes", metadata={"count": 0})

        output = f"Tracked processes ({len(self._tracked_processes)}):\n\n"
        for proc_id, process in self._tracked_processes.items():
            return_code = process.returncode
            status = "running" if return_code is None else f"exited ({return_code})"
            output += f"- **{proc_id}**: PID {process.pid}, {status}\n"

        return ToolResult(
            success=True,
            content=output,
            metadata={
                "count": len(self._tracked_processes),
                "processes": [
                    {"process_id": pid, "pid": p.pid, "return_code": p.returncode}
                    for pid, p in self._tracked_processes.items()
                ],
            },
        )

    async def _kill_process(self, params: dict[str, Any]) -> ToolResult:
        """Kill a process forcefully"""
        process_id = params.get("process_id")
        pid = params.get("pid")

        if process_id:
            if process_id not in self._tracked_processes:
                return ToolResult(
                    success=False, content="", error=f"Process '{process_id}' not found"
                )

            process = self._tracked_processes[process_id]
            process.kill()
            await process.wait()
            del self._tracked_processes[process_id]

            return ToolResult(success=True, content=f"Killed process '{process_id}'")

        elif pid:
            try:
                proc = psutil.Process(pid)
                proc.kill()
                return ToolResult(success=True, content=f"Killed process {pid}")
            except psutil.NoSuchProcess:
                return ToolResult(success=False, content="", error=f"Process {pid} not found")
            except ImportError:
                return ToolResult(success=False, content="", error="psutil not installed")
        else:
            return ToolResult(success=False, content="", error="process_id or pid required")

    async def _wait_process(self, params: dict[str, Any]) -> ToolResult:
        """Wait for process to complete"""
        process_id = params.get("process_id", "")

        if not process_id:
            return ToolResult(success=False, content="", error="process_id required")

        if process_id not in self._tracked_processes:
            return ToolResult(success=False, content="", error=f"Process '{process_id}' not found")

        process = self._tracked_processes[process_id]

        # Wait for completion
        stdout, stderr = await process.communicate()

        output = ""
        if stdout:
            output += stdout.decode("utf-8", errors="replace")
        if stderr:
            if output:
                output += "\n"
            output += stderr.decode("utf-8", errors="replace")

        # Remove from tracking
        del self._tracked_processes[process_id]

        return ToolResult(
            success=process.returncode == 0,
            content=output,
            metadata={"process_id": process_id, "exit_code": process.returncode},
        )
