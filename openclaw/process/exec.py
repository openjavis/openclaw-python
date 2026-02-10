"""Command execution utilities"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

logger = logging.getLogger(__name__)


@dataclass
class ExecResult:
    """Command execution result"""
    
    stdout: str
    stderr: str
    returncode: int
    duration: float


async def exec_command(
    command: str | list[str],
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> ExecResult:
    """
    Execute command and return result
    
    Args:
        command: Command to execute
        cwd: Working directory
        env: Environment variables
        timeout: Timeout in seconds
        
    Returns:
        Execution result
    """
    import time
    
    start_time = time.time()
    
    # Convert command to list
    if isinstance(command, str):
        cmd_list = command.split()
    else:
        cmd_list = command
    
    logger.debug(f"Executing: {' '.join(cmd_list)}")
    
    try:
        # Create subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd_list,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )
        
        # Wait with timeout
        if timeout:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        else:
            stdout, stderr = await process.communicate()
        
        duration = time.time() - start_time
        
        return ExecResult(
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            returncode=process.returncode,
            duration=duration,
        )
        
    except asyncio.TimeoutError:
        logger.error(f"Command timed out: {' '.join(cmd_list)}")
        process.kill()
        await process.wait()
        
        duration = time.time() - start_time
        
        return ExecResult(
            stdout="",
            stderr="Command timed out",
            returncode=-1,
            duration=duration,
        )
    
    except Exception as e:
        logger.error(f"Command execution error: {e}", exc_info=True)
        
        duration = time.time() - start_time
        
        return ExecResult(
            stdout="",
            stderr=str(e),
            returncode=-1,
            duration=duration,
        )


async def exec_command_stream(
    command: str | list[str],
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
) -> AsyncIterator[tuple[str, str]]:
    """
    Execute command and stream output
    
    Args:
        command: Command to execute
        cwd: Working directory
        env: Environment variables
        
    Yields:
        (stream_name, line) tuples ('stdout' or 'stderr')
    """
    # Convert command to list
    if isinstance(command, str):
        cmd_list = command.split()
    else:
        cmd_list = command
    
    logger.debug(f"Streaming: {' '.join(cmd_list)}")
    
    # Create subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd_list,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=env,
    )
    
    # Stream output
    async def stream_pipe(pipe, name):
        """Stream output from pipe"""
        while True:
            line = await pipe.readline()
            if not line:
                break
            yield (name, line.decode().rstrip())
    
    # Combine streams
    async for stream_name, line in _merge_streams(
        stream_pipe(process.stdout, "stdout"),
        stream_pipe(process.stderr, "stderr"),
    ):
        yield stream_name, line
    
    # Wait for process to complete
    await process.wait()


async def _merge_streams(*streams):
    """Merge multiple async iterators"""
    tasks = [asyncio.create_task(_to_queue(stream)) for stream in streams]
    
    while tasks:
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        for task in done:
            try:
                result = task.result()
                if result is not None:
                    yield result
            except StopAsyncIteration:
                pass
        
        tasks = list(tasks)


async def _to_queue(stream):
    """Convert async iterator to queue"""
    async for item in stream:
        return item
