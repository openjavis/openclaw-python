"""
Default implementations of operations interfaces

Provides standard local filesystem and subprocess implementations
for tool operations.
"""
from __future__ import annotations

import asyncio
import os
import signal as signal_module
from pathlib import Path
from typing import Callable

import aiofiles

from .operations import BashOperations, EditOperations, ReadOperations, WriteOperations


class DefaultBashOperations(BashOperations):
    """
    Default bash operations using asyncio subprocess.
    
    Executes commands locally using asyncio.create_subprocess_shell.
    """
    
    async def exec(
        self,
        command: str,
        cwd: str,
        on_data: Callable[[bytes], None],
        signal: asyncio.Event | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, int | None]:
        """Execute command using subprocess"""
        
        # Merge environment
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # Combine stderr with stdout
            cwd=cwd,
            env=merged_env,
        )
        
        # Handle cancellation
        cancelled = False
        
        def check_signal():
            nonlocal cancelled
            if signal and signal.is_set():
                cancelled = True
                if process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
        
        async def read_output():
            """Read output and call on_data"""
            nonlocal cancelled
            try:
                if process.stdout:
                    while True:
                        # Check cancellation
                        check_signal()
                        if cancelled:
                            break
                        
                        # Read chunk
                        chunk = await process.stdout.read(4096)
                        if not chunk:
                            break
                        
                        # Call callback
                        on_data(chunk)
            except asyncio.CancelledError:
                cancelled = True
                if process.returncode is None:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                raise
        
        # Run with timeout
        try:
            if timeout:
                await asyncio.wait_for(read_output(), timeout=timeout)
                await asyncio.wait_for(process.wait(), timeout=1.0)
            else:
                await read_output()
                await process.wait()
        except asyncio.TimeoutError:
            # Kill process on timeout
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            raise
        except asyncio.CancelledError:
            # Kill process on cancellation
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            raise
        
        return {"exit_code": process.returncode}


class DefaultReadOperations(ReadOperations):
    """
    Default read operations using aiofiles.
    
    Reads from local filesystem.
    """
    
    async def access(self, path: str) -> None:
        """Check if file is accessible"""
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not path_obj.is_file():
            raise ValueError(f"Not a file: {path}")
        
        if not os.access(path, os.R_OK):
            raise PermissionError(f"File not readable: {path}")
    
    async def read_file(self, path: str) -> bytes:
        """Read file contents"""
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()
    
    async def detect_image_mime_type(self, path: str) -> str | None:
        """Detect image MIME type from extension"""
        path_obj = Path(path)
        suffix = path_obj.suffix.lower()
        
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
        }
        
        return mime_types.get(suffix)


class DefaultWriteOperations(WriteOperations):
    """
    Default write operations using aiofiles.
    
    Writes to local filesystem.
    """
    
    async def mkdir(self, path: str) -> None:
        """Create directory recursively"""
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
    
    async def write_file(self, path: str, content: str) -> None:
        """Write file contents"""
        async with aiofiles.open(path, 'w', encoding='utf-8') as f:
            await f.write(content)


class DefaultEditOperations(DefaultReadOperations, DefaultWriteOperations, EditOperations):
    """
    Default edit operations combining read and write.
    
    Provides both read and write operations for editing workflow.
    """
    pass


__all__ = [
    "DefaultBashOperations",
    "DefaultReadOperations",
    "DefaultWriteOperations",
    "DefaultEditOperations",
]
