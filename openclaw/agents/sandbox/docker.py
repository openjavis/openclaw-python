"""Docker sandbox implementation

Provides isolated code execution using Docker containers.
Matches TypeScript openclaw/src/agents/sandbox/docker.ts
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import DEFAULT_SANDBOX_IMAGE, SANDBOX_AGENT_WORKSPACE_MOUNT

logger = logging.getLogger(__name__)


async def exec_docker(args: list[str], allow_failure: bool = False) -> dict[str, Any]:
    """
    Execute a Docker command
    
    Args:
        args: Docker command arguments
        allow_failure: If True, don't raise on non-zero exit
        
    Returns:
        Dict with stdout, stderr, code
        
    Raises:
        RuntimeError: If command fails and allow_failure=False
    """
    proc = await asyncio.create_subprocess_exec(
        "docker",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    
    stdout_bytes, stderr_bytes = await proc.communicate()
    stdout = stdout_bytes.decode() if stdout_bytes else ""
    stderr = stderr_bytes.decode() if stderr_bytes else ""
    code = proc.returncode or 0
    
    if code != 0 and not allow_failure:
        error_msg = stderr.strip() or f"docker {' '.join(args)} failed"
        raise RuntimeError(error_msg)
    
    return {
        "stdout": stdout,
        "stderr": stderr,
        "code": code,
    }


async def read_docker_port(container_name: str, port: int) -> int | None:
    """
    Read mapped port for a container
    
    Args:
        container_name: Container name
        port: Internal port
        
    Returns:
        Mapped external port or None
    """
    result = await exec_docker(
        ["port", container_name, f"{port}/tcp"],
        allow_failure=True
    )
    
    if result["code"] != 0:
        return None
    
    line = result["stdout"].strip().split('\n')[0]
    
    # Parse "0.0.0.0:12345" or "[::]:12345"
    import re
    match = re.search(r':(\d+)\s*$', line)
    if not match:
        return None
    
    mapped = int(match.group(1))
    return mapped if mapped > 0 else None


async def docker_image_exists(image: str) -> bool:
    """
    Check if a Docker image exists locally
    
    Args:
        image: Image name
        
    Returns:
        True if image exists
    """
    result = await exec_docker(["image", "inspect", image], allow_failure=True)
    
    if result["code"] == 0:
        return True
    
    stderr = result["stderr"].strip()
    if "No such image" in stderr:
        return False
    
    raise RuntimeError(f"Failed to inspect sandbox image: {stderr}")


async def ensure_docker_image(image: str):
    """
    Ensure Docker image exists, pulling if necessary
    
    Args:
        image: Image name
        
    Raises:
        RuntimeError: If image cannot be obtained
    """
    exists = await docker_image_exists(image)
    if exists:
        return
    
    if image == DEFAULT_SANDBOX_IMAGE:
        # Pull debian base and tag as default
        logger.info("Pulling default sandbox image...")
        await exec_docker(["pull", "debian:bookworm-slim"])
        await exec_docker(["tag", "debian:bookworm-slim", DEFAULT_SANDBOX_IMAGE])
        logger.info("Default sandbox image ready")
        return
    
    raise RuntimeError(
        f"Sandbox image not found: {image}. Build or pull it first."
    )


async def docker_container_state(name: str) -> dict[str, bool]:
    """
    Get container state
    
    Args:
        name: Container name
        
    Returns:
        Dict with exists and running booleans
    """
    result = await exec_docker(
        ["inspect", "-f", "{{.State.Running}}", name],
        allow_failure=True
    )
    
    if result["code"] != 0:
        return {"exists": False, "running": False}
    
    running = result["stdout"].strip() == "true"
    return {"exists": True, "running": running}


def normalize_docker_limit(value: str | int | None) -> str | None:
    """Normalize Docker resource limit value"""
    if value is None:
        return None
    
    if isinstance(value, int):
        return str(value) if value > 0 else None
    
    trimmed = str(value).strip()
    return trimmed if trimmed else None


@dataclass
class DockerSandboxConfig:
    """Docker sandbox configuration"""
    
    image: str = DEFAULT_SANDBOX_IMAGE
    memory: str | None = None  # e.g. "512m", "1g"
    cpus: str | None = None  # e.g. "0.5", "2"
    cpu_shares: int | None = None
    ulimits: dict[str, dict[str, int]] | None = None
    workspace_access: str = "read-write"  # "read-only", "read-write", "none"
    network_mode: str = "bridge"  # "bridge", "none", "host"
    env: dict[str, str] = field(default_factory=dict)
    volumes: dict[str, str] = field(default_factory=dict)  # host_path: container_path
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for hashing"""
        return {
            "image": self.image,
            "memory": self.memory,
            "cpus": self.cpus,
            "cpu_shares": self.cpu_shares,
            "ulimits": self.ulimits,
            "workspace_access": self.workspace_access,
            "network_mode": self.network_mode,
            "env": self.env,
            "volumes": self.volumes,
        }


class DockerSandbox:
    """Docker sandbox manager for isolated code execution"""
    
    def __init__(self, config: DockerSandboxConfig, workspace_dir: Path | None = None):
        """
        Initialize Docker sandbox
        
        Args:
            config: Sandbox configuration
            workspace_dir: Workspace directory to mount
        """
        self.config = config
        self.workspace_dir = workspace_dir
        self.container_name: str | None = None
        self._started = False
    
    async def start(self) -> str:
        """
        Start sandbox container
        
        Returns:
            Container name
        """
        if self._started:
            return self.container_name or ""
        
        # Ensure image exists
        await ensure_docker_image(self.config.image)
        
        # Generate container name
        import uuid
        import time
        
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        self.container_name = f"openclaw-sandbox-{timestamp}-{unique_id}"
        
        # Build docker run command
        args = ["run", "-d", "--name", self.container_name]
        
        # Resource limits
        if self.config.memory:
            mem = normalize_docker_limit(self.config.memory)
            if mem:
                args.extend(["--memory", mem])
        
        if self.config.cpus:
            cpus = normalize_docker_limit(self.config.cpus)
            if cpus:
                args.extend(["--cpus", cpus])
        
        if self.config.cpu_shares:
            args.extend(["--cpu-shares", str(self.config.cpu_shares)])
        
        # ulimits
        if self.config.ulimits:
            for name, limits in self.config.ulimits.items():
                soft = limits.get("soft")
                hard = limits.get("hard", soft)
                if soft is not None:
                    args.extend(["--ulimit", f"{name}={soft}:{hard}"])
        
        # Network
        args.extend(["--network", self.config.network_mode])
        
        # Environment variables
        for key, value in self.config.env.items():
            args.extend(["-e", f"{key}={value}"])
        
        # Workspace mount
        if self.workspace_dir and self.config.workspace_access != "none":
            mount_mode = "ro" if self.config.workspace_access == "read-only" else "rw"
            args.extend([
                "-v",
                f"{self.workspace_dir}:{SANDBOX_AGENT_WORKSPACE_MOUNT}:{mount_mode}"
            ])
        
        # Additional volumes
        for host_path, container_path in self.config.volumes.items():
            args.extend(["-v", f"{host_path}:{container_path}"])
        
        # Image and command (keep container running)
        args.extend([self.config.image, "tail", "-f", "/dev/null"])
        
        logger.info(f"Starting sandbox container: {self.container_name}")
        
        # Run container
        await exec_docker(args)
        
        self._started = True
        return self.container_name
    
    async def stop(self):
        """Stop and remove sandbox container"""
        if not self.container_name:
            return
        
        logger.info(f"Stopping sandbox container: {self.container_name}")
        
        # Stop container
        await exec_docker(["stop", self.container_name], allow_failure=True)
        
        # Remove container
        await exec_docker(["rm", self.container_name], allow_failure=True)
        
        self._started = False
    
    async def exec_command(self, cmd: str, **kwargs) -> dict[str, Any]:
        """
        Execute command in sandbox container
        
        Args:
            cmd: Shell command to execute
            **kwargs: Additional options (timeout_ms, etc.)
            
        Returns:
            Dict with stdout, stderr, exit_code
        """
        if not self.container_name or not self._started:
            raise RuntimeError("Sandbox not started")
        
        # Build exec command
        args = ["exec", self.container_name, "sh", "-c", cmd]
        
        # Execute
        result = await exec_docker(args, allow_failure=True)
        
        return {
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["code"],
            "success": result["code"] == 0,
        }
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.stop()
