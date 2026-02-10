"""Docker sandbox system for isolated code execution

Matches TypeScript openclaw/src/agents/sandbox/
"""

from .docker import (
    DockerSandbox,
    DockerSandboxConfig,
    exec_docker,
    ensure_docker_image,
    docker_container_state,
)
from .constants import DEFAULT_SANDBOX_IMAGE, SANDBOX_AGENT_WORKSPACE_MOUNT
from .config_hash import compute_sandbox_config_hash
from .registry import SandboxRegistry, get_sandbox_registry

__all__ = [
    "DockerSandbox",
    "DockerSandboxConfig",
    "exec_docker",
    "ensure_docker_image",
    "docker_container_state",
    "DEFAULT_SANDBOX_IMAGE",
    "SANDBOX_AGENT_WORKSPACE_MOUNT",
    "compute_sandbox_config_hash",
    "SandboxRegistry",
    "get_sandbox_registry",
]
