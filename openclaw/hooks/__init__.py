"""Hooks system for event-driven extensibility.

Aligned with TypeScript src/hooks/types.ts
"""

from __future__ import annotations

from .loader import load_hooks_from_dir
from .registry import HookRegistry, get_hook_registry
from .types import (
    Hook,
    HookEntry,
    HookInstallSpec,
    HookInvocationPolicy,
    HookSnapshot,
    HookSource,
    OpenClawHookMetadata,
)
from .workspace import build_workspace_hook_snapshot, load_workspace_hook_entries

__all__ = [
    "Hook",
    "HookEntry",
    "HookSource",
    "HookSnapshot",
    "OpenClawHookMetadata",
    "HookInstallSpec",
    "HookInvocationPolicy",
    "load_hooks_from_dir",
    "load_workspace_hook_entries",
    "build_workspace_hook_snapshot",
    "HookRegistry",
    "get_hook_registry",
]
