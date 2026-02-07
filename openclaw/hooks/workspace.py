"""Workspace hooks management.

Load and merge hooks from multiple sources.
Aligned with TypeScript src/hooks/workspace.ts
"""

from __future__ import annotations

from pathlib import Path

from .loader import load_hooks_from_dir
from .types import HookEntry, HookSnapshot


def load_workspace_hook_entries(
    workspace_dir: Path | None = None,
    managed_dir: Path | None = None,
    bundled_dir: Path | None = None,
    extra_dirs: list[Path] | None = None,
) -> list[HookEntry]:
    """Load hook entries from multiple sources with priority.

    Priority order (highest to lowest):
    1. Workspace hooks (workspace/hooks)
    2. Managed hooks (~/.openclaw/hooks)
    3. Extra directories
    4. Bundled hooks

    Args:
        workspace_dir: Workspace directory
        managed_dir: Managed hooks directory
        bundled_dir: Bundled hooks directory
        extra_dirs: Additional directories

    Returns:
        List of HookEntry objects (merged, deduplicated)
    """
    all_hooks: dict[str, HookEntry] = {}

    # Load bundled hooks (lowest priority)
    if bundled_dir and bundled_dir.exists():
        bundled_hooks = load_hooks_from_dir(bundled_dir, "openclaw-bundled")
        for entry in bundled_hooks:
            all_hooks[entry.hook.name] = entry

    # Load extra directories
    if extra_dirs:
        for extra_dir in extra_dirs:
            if extra_dir.exists():
                extra_hooks = load_hooks_from_dir(extra_dir, "openclaw-managed")
                for entry in extra_hooks:
                    all_hooks[entry.hook.name] = entry

    # Load managed hooks
    if managed_dir and managed_dir.exists():
        managed_hooks = load_hooks_from_dir(managed_dir, "openclaw-managed")
        for entry in managed_hooks:
            all_hooks[entry.hook.name] = entry

    # Load workspace hooks (highest priority)
    if workspace_dir:
        workspace_hooks_dir = workspace_dir / "hooks"
        if workspace_hooks_dir.exists():
            workspace_hooks = load_hooks_from_dir(workspace_hooks_dir, "openclaw-workspace")
            for entry in workspace_hooks:
                all_hooks[entry.hook.name] = entry

    return list(all_hooks.values())


def build_workspace_hook_snapshot(hook_entries: list[HookEntry]) -> HookSnapshot:
    """Build a snapshot of hook state.

    Args:
        hook_entries: List of hook entries

    Returns:
        HookSnapshot with current state
    """
    hooks_data = []
    resolved_hooks = []

    for entry in hook_entries:
        hook = entry.hook
        metadata = entry.metadata

        hooks_data.append({"name": hook.name, "events": metadata.events if metadata else []})

        resolved_hooks.append(hook)

    return HookSnapshot(hooks=hooks_data, resolved_hooks=resolved_hooks, version=1)
