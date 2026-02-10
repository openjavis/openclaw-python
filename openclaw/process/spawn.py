"""Process spawning utilities"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SpawnedProcess:
    """Spawned process handle"""
    
    pid: int
    process: asyncio.subprocess.Process
    command: list[str]
    
    async def wait(self) -> int:
        """Wait for process to complete"""
        return await self.process.wait()
    
    async def kill(self) -> None:
        """Kill process"""
        self.process.kill()
        await self.process.wait()
    
    async def terminate(self) -> None:
        """Terminate process gracefully"""
        self.process.terminate()
        await self.process.wait()
    
    def is_running(self) -> bool:
        """Check if process is still running"""
        return self.process.returncode is None


async def spawn_process(
    command: str | list[str],
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    stdout: Any = None,
    stderr: Any = None,
) -> SpawnedProcess:
    """
    Spawn background process
    
    Args:
        command: Command to execute
        cwd: Working directory
        env: Environment variables
        stdout: Stdout destination
        stderr: Stderr destination
        
    Returns:
        Spawned process handle
    """
    # Convert command to list
    if isinstance(command, str):
        cmd_list = command.split()
    else:
        cmd_list = command
    
    logger.info(f"Spawning process: {' '.join(cmd_list)}")
    
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd_list,
        stdout=stdout or asyncio.subprocess.PIPE,
        stderr=stderr or asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )
    
    return SpawnedProcess(
        pid=process.pid,
        process=process,
        command=cmd_list,
    )
