"""Hook loading from directories.

Loads HOOK.md files and their handlers.
Aligned with TypeScript src/hooks/loader.ts
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .types import Hook, HookEntry, HookInvocationPolicy, HookSource, OpenClawHookMetadata


def parse_hook_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from HOOK.md.

    Args:
        content: Full file content

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    if not content.startswith("---"):
        return {}, content

    # Find end of frontmatter
    end_index = content.find("---", 3)
    if end_index == -1:
        return {}, content

    # Extract frontmatter and body
    frontmatter_text = content[3:end_index].strip()
    body = content[end_index + 3 :].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, body


def extract_hook_metadata(frontmatter: dict) -> OpenClawHookMetadata | None:
    """Extract OpenClaw hook metadata from frontmatter.

    Args:
        frontmatter: Parsed frontmatter dictionary

    Returns:
        OpenClawHookMetadata if 'openclaw' key present, None otherwise
    """
    openclaw_data = frontmatter.get("openclaw")
    if not openclaw_data or not isinstance(openclaw_data, dict):
        return None

    events = openclaw_data.get("events", [])
    if not isinstance(events, list):
        events = [events] if events else []

    return OpenClawHookMetadata(
        events=events,
        always=openclaw_data.get("always", False),
        hook_key=openclaw_data.get("hookKey"),
        emoji=openclaw_data.get("emoji"),
        homepage=openclaw_data.get("homepage"),
        export=openclaw_data.get("export", "default"),
        os=openclaw_data.get("os"),
        requires=openclaw_data.get("requires"),
        install=openclaw_data.get("install"),
    )


def load_hook_from_dir(hook_dir: Path, source: HookSource) -> HookEntry | None:
    """Load a hook from a directory containing HOOK.md.

    Args:
        hook_dir: Directory containing HOOK.md
        source: Hook source

    Returns:
        HookEntry if valid hook found, None otherwise
    """
    hook_md_path = hook_dir / "HOOK.md"
    if not hook_md_path.exists():
        return None

    try:
        content = hook_md_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Parse frontmatter
    frontmatter, body = parse_hook_frontmatter(content)

    # Extract name and description
    name = frontmatter.get("name", hook_dir.name)
    description = frontmatter.get("description", "")

    # If no description in frontmatter, try to extract from body
    if not description and body:
        lines = body.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                description = line
                break

    # Find handler file
    handler_path = ""
    for handler_file in ["handler.py", "handler.js", "handler.ts"]:
        handler_file_path = hook_dir / handler_file
        if handler_file_path.exists():
            handler_path = str(handler_file_path)
            break

    # Create hook
    hook = Hook(
        name=name,
        description=description,
        source=source,
        file_path=str(hook_md_path),
        base_dir=str(hook_dir),
        handler_path=handler_path,
    )

    # Extract metadata
    metadata = extract_hook_metadata(frontmatter)

    # Create entry
    entry = HookEntry(
        hook=hook,
        frontmatter=frontmatter,
        metadata=metadata,
        invocation=HookInvocationPolicy(enabled=True),
    )

    return entry


def load_hooks_from_dir(
    directory: Path, source: HookSource = "openclaw-workspace"
) -> list[HookEntry]:
    """Load all hooks from a directory.

    Scans for subdirectories containing HOOK.md files.

    Args:
        directory: Directory to scan
        source: Hook source

    Returns:
        List of HookEntry objects
    """
    if not directory.exists() or not directory.is_dir():
        return []

    hooks: list[HookEntry] = []

    # Scan subdirectories
    for subdir in directory.iterdir():
        if not subdir.is_dir():
            continue

        # Try to load hook from this directory
        entry = load_hook_from_dir(subdir, source)
        if entry:
            hooks.append(entry)

    return hooks


def format_hooks_for_display(hooks: list[HookEntry]) -> str:
    """Format hooks for human-readable display.

    Args:
        hooks: List of hook entries

    Returns:
        Formatted string
    """
    if not hooks:
        return "No hooks available."

    lines = []
    for entry in hooks:
        hook = entry.hook
        emoji = entry.metadata.emoji if entry.metadata else ""
        events = entry.metadata.events if entry.metadata else []
        events_str = ", ".join(events) if events else "no events"

        prefix = f"{emoji} " if emoji else ""
        lines.append(f"{prefix}**{hook.name}**")
        lines.append(f"  {hook.description}")
        lines.append(f"  Events: {events_str}")
        lines.append("")

    return "\n".join(lines)
