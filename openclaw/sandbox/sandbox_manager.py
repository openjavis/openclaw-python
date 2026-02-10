"""Sandbox manager for isolated code execution"""

import asyncio
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SandboxResult:
    """Result from sandbox execution"""
    
    def __init__(self, stdout: str, stderr: str, exit_code: int, files: dict[str, bytes]):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.files = files  # Output files from sandbox
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0


class SandboxManager:
    """
    Sandbox manager for isolated code execution.
    
    Provides:
    - Docker container-based isolation
    - File system restrictions
    - Network restrictions
    - Resource limits
    """
    
    def __init__(
        self,
        use_docker: bool = True,
        default_image: str = "python:3.11-slim",
        timeout_sec: int = 30,
    ):
        self.use_docker = use_docker
        self.default_image = default_image
        self.timeout_sec = timeout_sec
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        files: dict[str, bytes] | None = None,
        timeout_sec: int | None = None,
    ) -> SandboxResult:
        """
        Execute code in sandbox.
        
        Args:
            code: Code to execute
            language: Programming language (python, javascript, bash)
            files: Input files {filename: content}
            timeout_sec: Execution timeout (overrides default)
        
        Returns:
            SandboxResult with output and files
        """
        timeout = timeout_sec or self.timeout_sec
        
        if self.use_docker:
            return await self._execute_docker(code, language, files, timeout)
        else:
            return await self._execute_local(code, language, files, timeout)
    
    async def _execute_docker(
        self,
        code: str,
        language: str,
        files: dict[str, bytes] | None,
        timeout_sec: int,
    ) -> SandboxResult:
        """Execute in Docker container"""
        
        # Check if docker is available
        if not shutil.which("docker"):
            logger.warning("Docker not available, falling back to local execution")
            return await self._execute_local(code, language, files, timeout_sec)
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write input files
            if files:
                for filename, content in files.items():
                    (tmppath / filename).write_bytes(content)
            
            # Write code file
            if language == "python":
                code_file = "script.py"
                (tmppath / code_file).write_text(code)
                cmd = ["python", code_file]
            elif language == "javascript":
                code_file = "script.js"
                (tmppath / code_file).write_text(code)
                cmd = ["node", code_file]
            elif language == "bash":
                code_file = "script.sh"
                (tmppath / code_file).write_text(code)
                cmd = ["bash", code_file]
            else:
                raise ValueError(f"Unsupported language: {language}")
            
            # Run docker container
            docker_cmd = [
                "docker", "run",
                "--rm",
                "--network", "none",  # No network access
                "--memory", "256m",  # Memory limit
                "--cpus", "1",  # CPU limit
                "-v", f"{tmppath}:/workspace:rw",
                "-w", "/workspace",
                self.default_image,
                *cmd,
            ]
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_sec,
                )
                
                exit_code = proc.returncode
            
            except asyncio.TimeoutError:
                proc.kill()
                return SandboxResult(
                    stdout="",
                    stderr=f"Execution timed out after {timeout_sec}s",
                    exit_code=-1,
                    files={},
                )
            
            # Read output files
            output_files = {}
            for file in tmppath.iterdir():
                if file.name not in [code_file] and file.is_file():
                    output_files[file.name] = file.read_bytes()
            
            return SandboxResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=exit_code,
                files=output_files,
            )
    
    async def _execute_local(
        self,
        code: str,
        language: str,
        files: dict[str, bytes] | None,
        timeout_sec: int,
    ) -> SandboxResult:
        """Execute locally (less secure, for development)"""
        
        logger.warning("Executing in local mode - not sandboxed!")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write input files
            if files:
                for filename, content in files.items():
                    (tmppath / filename).write_bytes(content)
            
            # Write and execute code
            if language == "python":
                code_file = tmppath / "script.py"
                code_file.write_text(code)
                cmd = ["python", str(code_file)]
            elif language == "javascript":
                code_file = tmppath / "script.js"
                code_file.write_text(code)
                cmd = ["node", str(code_file)]
            elif language == "bash":
                code_file = tmppath / "script.sh"
                code_file.write_text(code)
                cmd = ["bash", str(code_file)]
            else:
                raise ValueError(f"Unsupported language: {language}")
            
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmppath,
                )
                
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_sec,
                )
                
                exit_code = proc.returncode
            
            except asyncio.TimeoutError:
                proc.kill()
                return SandboxResult(
                    stdout="",
                    stderr=f"Execution timed out after {timeout_sec}s",
                    exit_code=-1,
                    files={},
                )
            
            # Read output files
            output_files = {}
            for file in tmppath.iterdir():
                if file != code_file and file.is_file():
                    output_files[file.name] = file.read_bytes()
            
            return SandboxResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=exit_code,
                files=output_files,
            )
