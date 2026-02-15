"""Extension type definitions

Extensions run IN the agent runtime, not the gateway.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol


@dataclass
class ExtensionManifest:
    """Extension manifest (extension.json)"""
    name: str
    version: str
    description: str
    author: str | None = None
    main: str = "extension.py"
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


@dataclass
class ExtensionContext:
    """Context passed to extensions"""
    extension_dir: Path | None = None
    agent_id: str = "main"
    session_id: str | None = None
    workspace_dir: str | None = None  # Added for memory extension compatibility
    logger: Any | None = None  # Added for logging support
    config: dict[str, Any] = field(default_factory=dict)


class Extension(Protocol):
    """
    Extension protocol
    
    Extensions must implement:
    - register(api: ExtensionAPI) -> None
    """
    
    def register(self, api: "ExtensionAPI") -> None:
        """Register extension capabilities"""
        ...
