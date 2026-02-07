"""Hook type definitions.

Aligned with TypeScript src/hooks/types.ts
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class HookInstallSpec:
    """Installation specification for a hook."""

    id: str | None = None
    kind: Literal["bundled", "npm", "git"] = "bundled"
    label: str | None = None
    package: str | None = None
    repository: str | None = None
    bins: list[str] | None = None


@dataclass
class OpenClawHookMetadata:
    """OpenClaw-specific hook metadata from HOOK.md frontmatter."""

    events: list[str] = field(default_factory=list)  # Events this hook handles
    always: bool = False  # Always load this hook
    hook_key: str | None = None
    emoji: str | None = None
    homepage: str | None = None
    export: str = "default"  # Export name (default: "default")
    os: list[str] | None = None  # Supported OS
    requires: dict[str, Any] | None = None  # Requirements
    install: list[HookInstallSpec] | None = None


@dataclass
class HookInvocationPolicy:
    """Hook invocation policy."""

    enabled: bool = True


HookSource = Literal[
    "openclaw-bundled", "openclaw-managed", "openclaw-workspace", "openclaw-plugin"
]


@dataclass
class Hook:
    """A hook definition."""

    name: str
    description: str
    source: HookSource
    plugin_id: str | None = None
    file_path: str = ""  # Path to HOOK.md
    base_dir: str = ""  # Directory containing hook
    handler_path: str = ""  # Path to handler module


@dataclass
class HookEntry:
    """Hook entry with metadata."""

    hook: Hook
    frontmatter: dict[str, str] = field(default_factory=dict)
    metadata: OpenClawHookMetadata | None = None
    invocation: HookInvocationPolicy | None = None


@dataclass
class HookEligibilityContext:
    """Context for determining hook eligibility."""

    remote: dict[str, Any] | None = None


@dataclass
class HookSnapshot:
    """Snapshot of current hooks state."""

    hooks: list[dict[str, Any]] = field(default_factory=list)
    resolved_hooks: list[Hook] | None = None
    version: int = 1


# Hook handler type
HookHandler = Callable[[dict[str, Any]], Awaitable[None]]
