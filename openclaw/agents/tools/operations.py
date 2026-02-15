"""
Pluggable operations interfaces for tools

This module defines abstract interfaces for tool operations,
allowing for:
- Remote execution (SSH, Docker, etc.)
- Testing with mocks
- Custom implementations

Matches pi-mono's pluggable operations pattern.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Callable


class BashOperations(ABC):
    """
    Abstract interface for bash command execution.
    
    Allows plugging in different execution backends:
    - Local: subprocess
    - Remote: SSH
    - Container: Docker/Kubernetes
    - Mock: for testing
    """
    
    @abstractmethod
    async def exec(
        self,
        command: str,
        cwd: str,
        on_data: Callable[[bytes], None],
        signal: asyncio.Event | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, int | None]:
        """
        Execute a bash command.
        
        Args:
            command: Command to execute
            cwd: Working directory
            on_data: Callback for streaming output (called with each chunk)
            signal: Cancellation signal (check with signal.is_set())
            timeout: Timeout in seconds (None for no timeout)
            env: Environment variables (None to inherit)
            
        Returns:
            Dict with 'exit_code' (int | None, None if killed)
            
        Raises:
            asyncio.CancelledError: If signal is set
            asyncio.TimeoutError: If timeout exceeded
            Exception: Other errors
        """
        pass


class ReadOperations(ABC):
    """
    Abstract interface for file reading operations.
    
    Allows plugging in different backends:
    - Local: pathlib/aiofiles
    - Remote: SFTP/SSH
    - Cloud: S3/GCS
    - Mock: for testing
    """
    
    @abstractmethod
    async def access(self, path: str) -> None:
        """
        Check if file is accessible.
        
        Args:
            path: Absolute file path
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file isn't accessible
        """
        pass
    
    @abstractmethod
    async def read_file(self, path: str) -> bytes:
        """
        Read file contents.
        
        Args:
            path: Absolute file path
            
        Returns:
            File contents as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file isn't readable
        """
        pass
    
    @abstractmethod
    async def detect_image_mime_type(self, path: str) -> str | None:
        """
        Detect if file is an image and return MIME type.
        
        Args:
            path: Absolute file path
            
        Returns:
            MIME type if image (e.g., "image/png"), None otherwise
        """
        pass


class WriteOperations(ABC):
    """
    Abstract interface for file writing operations.
    
    Allows plugging in different backends:
    - Local: pathlib/aiofiles
    - Remote: SFTP/SSH
    - Cloud: S3/GCS
    - Mock: for testing
    """
    
    @abstractmethod
    async def mkdir(self, path: str) -> None:
        """
        Create directory (recursive).
        
        Args:
            path: Absolute directory path
            
        Raises:
            PermissionError: If directory can't be created
        """
        pass
    
    @abstractmethod
    async def write_file(self, path: str, content: str) -> None:
        """
        Write file contents.
        
        Args:
            path: Absolute file path
            content: File contents to write
            
        Raises:
            PermissionError: If file can't be written
        """
        pass


class EditOperations(ReadOperations, WriteOperations):
    """
    Abstract interface for file editing operations.
    
    Combines read and write operations for editing workflow.
    """
    pass


__all__ = [
    "BashOperations",
    "ReadOperations",
    "WriteOperations",
    "EditOperations",
]
