"""
Tool execution permission policies.

Matches TypeScript src/agents/tool-policy.ts:
  - TOOL_NAME_ALIASES
  - TOOL_GROUPS
  - TOOL_PROFILES (minimal / coding / messaging / full)
  - OWNER_ONLY_TOOL_NAMES
  - normalize / expand / resolve helpers
  - Owner-only tool guard
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Tool-name aliases (matches TS TOOL_NAME_ALIASES)
# ──────────────────────────────────────────────────────────────────────

TOOL_NAME_ALIASES: dict[str, str] = {
    # TS uses "exec" internally; Python uses "bash".  Keep both directions
    # so that config written for either runtime resolves correctly.
    "exec": "bash",
    "apply-patch": "apply_patch",
    # Python-specific reverse alias (TS config may reference "read"/"write"/"edit")
    "read": "read_file",
    "write": "write_file",
    "edit": "edit_file",
}


# ──────────────────────────────────────────────────────────────────────
# Tool groups (matches TS TOOL_GROUPS)
# NOTE: group tool names use Python canonical names (read_file, bash, …)
# ──────────────────────────────────────────────────────────────────────

TOOL_GROUPS: dict[str, list[str]] = {
    # Memory tools
    "group:memory": ["memory_search", "memory_get"],
    # Web tools
    "group:web": ["web_search", "web_fetch"],
    # Basic workspace/file tools
    "group:fs": ["read_file", "write_file", "edit_file", "apply_patch"],
    # Host/runtime execution tools
    "group:runtime": ["bash", "process"],
    # Session management tools
    "group:sessions": [
        "sessions_list",
        "sessions_history",
        "sessions_send",
        "sessions_spawn",
        "session_status",
    ],
    # UI helpers
    "group:ui": ["browser", "canvas"],
    # Automation + infra
    "group:automation": ["cron", "gateway"],
    # Messaging surface
    "group:messaging": ["message"],
    # Nodes + device tools
    "group:nodes": ["nodes"],
    # All OpenClaw native tools (excludes provider plugins)
    "group:openclaw": [
        "browser",
        "canvas",
        "nodes",
        "cron",
        "message",
        "gateway",
        "agents_list",
        "sessions_list",
        "sessions_history",
        "sessions_send",
        "sessions_spawn",
        "session_status",
        "memory_search",
        "memory_get",
        "web_search",
        "web_fetch",
        "image",
    ],
}


# ──────────────────────────────────────────────────────────────────────
# Owner-only tools (matches TS OWNER_ONLY_TOOL_NAMES)
# ──────────────────────────────────────────────────────────────────────

OWNER_ONLY_TOOL_NAMES: set[str] = {"whatsapp_login"}


# ──────────────────────────────────────────────────────────────────────
# Tool profile IDs (matches TS ToolProfileId)
# ──────────────────────────────────────────────────────────────────────

ToolProfileId = str  # "minimal" | "coding" | "messaging" | "full"


class ToolProfilePolicy:
    """A tool profile allow/deny policy."""

    def __init__(
        self,
        allow: list[str] | None = None,
        deny: list[str] | None = None,
    ):
        self.allow = allow
        self.deny = deny

    def __repr__(self) -> str:
        return f"ToolProfilePolicy(allow={self.allow}, deny={self.deny})"


# Matches TS TOOL_PROFILES exactly
TOOL_PROFILES: dict[ToolProfileId, ToolProfilePolicy] = {
    "minimal": ToolProfilePolicy(allow=["session_status"]),
    "coding": ToolProfilePolicy(
        allow=["group:fs", "group:runtime", "group:sessions", "group:memory", "image"]
    ),
    "messaging": ToolProfilePolicy(
        allow=[
            "group:messaging",
            "sessions_list",
            "sessions_history",
            "sessions_send",
            "session_status",
        ]
    ),
    "full": ToolProfilePolicy(),  # no restrictions
}


# ──────────────────────────────────────────────────────────────────────
# Normalisation helpers
# ──────────────────────────────────────────────────────────────────────


def normalize_tool_name(name: str) -> str:
    """Normalize and resolve tool name alias (matches TS normalizeToolName)."""
    normalized = name.strip().lower()
    return TOOL_NAME_ALIASES.get(normalized, normalized)


def normalize_tool_list(names: list[str] | None) -> list[str]:
    """Normalize a list of tool names (matches TS normalizeToolList)."""
    if not names:
        return []
    return [n for n in (normalize_tool_name(n) for n in names) if n]


def expand_tool_groups(names: list[str] | None) -> list[str]:
    """Expand group references to individual tool names (matches TS expandToolGroups)."""
    normalized = normalize_tool_list(names)
    expanded: list[str] = []
    for value in normalized:
        group = TOOL_GROUPS.get(value)
        if group:
            expanded.extend(group)
        else:
            expanded.append(value)
    # De-duplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for item in expanded:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ──────────────────────────────────────────────────────────────────────
# Owner-only guard
# ──────────────────────────────────────────────────────────────────────


def is_owner_only_tool_name(name: str) -> bool:
    """Check if a tool requires owner access (matches TS isOwnerOnlyToolName)."""
    return normalize_tool_name(name) in OWNER_ONLY_TOOL_NAMES


def apply_owner_only_tool_policy(
    tools: list[Any],
    sender_is_owner: bool,
) -> list[Any]:
    """
    Filter / guard tools based on owner-only policy (matches TS applyOwnerOnlyToolPolicy).

    For non-owner senders:
    - Owner-only tools are removed from the list entirely
    - (In TS, a wrapped execute() that throws is used first, then filtered)

    Args:
        tools: List of tool objects (must have a ``name`` attribute)
        sender_is_owner: Whether the current sender is the owner

    Returns:
        Filtered tool list
    """
    if sender_is_owner:
        return tools
    return [t for t in tools if not is_owner_only_tool_name(t.name)]


# ──────────────────────────────────────────────────────────────────────
# Profile resolution
# ──────────────────────────────────────────────────────────────────────


def resolve_tool_profile_policy(
    profile: str | None,
) -> ToolProfilePolicy | None:
    """Resolve a profile name to a ToolProfilePolicy (matches TS resolveToolProfilePolicy)."""
    if not profile:
        return None
    resolved = TOOL_PROFILES.get(profile)
    if not resolved:
        return None
    if not resolved.allow and not resolved.deny:
        return None  # "full" profile → no restrictions
    return ToolProfilePolicy(
        allow=list(resolved.allow) if resolved.allow else None,
        deny=list(resolved.deny) if resolved.deny else None,
    )


# ──────────────────────────────────────────────────────────────────────
# Sandbox mode
# ──────────────────────────────────────────────────────────────────────


class SandboxMode(Enum):
    """Sandbox modes for tool execution."""

    OFF = "off"
    NON_MAIN = "non-main"
    ALL = "all"


# ──────────────────────────────────────────────────────────────────────
# ToolPolicy: allow / deny evaluation
# ──────────────────────────────────────────────────────────────────────


class ToolPolicy:
    """
    Represents a tool allow/deny policy.

    Deny list takes precedence over allow list.
    """

    def __init__(
        self,
        allow: list[str] | None = None,
        deny: list[str] | None = None,
    ):
        self.allow = allow or []
        self.deny = deny or []

    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed by this policy."""
        normalized = normalize_tool_name(tool_name)

        # Deny list takes precedence
        if normalized in self.deny:
            return False

        # If allow list exists, tool must be in it (with group expansion)
        if self.allow:
            expanded_allow = expand_tool_groups(self.allow)
            return normalized in expanded_allow or "*" in self.allow

        # No restrictions
        return True

    def __repr__(self) -> str:
        return f"ToolPolicy(allow={self.allow}, deny={self.deny})"


# ──────────────────────────────────────────────────────────────────────
# ToolPolicyResolver: config-driven evaluation
# ──────────────────────────────────────────────────────────────────────


class ToolPolicyResolver:
    """Resolves and enforces tool policies from config."""

    def __init__(self, config: dict):
        self.config = config

    def is_tool_allowed(
        self,
        tool_name: str,
        agent_id: str,
        session_type: str = "main",
        is_main_session: bool = True,
    ) -> tuple[bool, str | None]:
        """
        Check if a tool can be executed.

        Returns:
            (allowed, reason_if_denied)
        """
        policies = self._get_policies(agent_id, is_main_session)

        for policy in policies:
            if not policy.is_allowed(tool_name):
                return False, f"Tool '{tool_name}' denied by policy"

        return True, None

    def _get_policies(
        self,
        agent_id: str,
        is_main_session: bool,
    ) -> list[ToolPolicy]:
        """Get all applicable policies in order."""
        policies: list[ToolPolicy] = []

        # 1. Global tools policy
        global_tools = self.config.get("tools", {})
        if global_tools.get("allow") or global_tools.get("deny"):
            policies.append(
                ToolPolicy(
                    allow=global_tools.get("allow"),
                    deny=global_tools.get("deny"),
                )
            )

        # 2. Agent-specific policy
        agent_config = self._get_agent_config(agent_id)
        agent_tools = agent_config.get("tools", {})
        if agent_tools.get("allow") or agent_tools.get("deny"):
            policies.append(
                ToolPolicy(
                    allow=agent_tools.get("allow"),
                    deny=agent_tools.get("deny"),
                )
            )

        # 3. Tool profile
        profile = agent_config.get("tools", {}).get("profile")
        if profile:
            profile_policy = resolve_tool_profile_policy(profile)
            if profile_policy:
                policies.append(
                    ToolPolicy(
                        allow=expand_tool_groups(profile_policy.allow),
                        deny=expand_tool_groups(profile_policy.deny),
                    )
                )

        # 4. Sandbox policy (for non-main sessions)
        sandbox_mode = self._get_sandbox_mode()
        if self._should_apply_sandbox(sandbox_mode, is_main_session):
            sandbox_policy = self._get_sandbox_policy(agent_config)
            if sandbox_policy:
                policies.append(sandbox_policy)

        return policies

    def _get_agent_config(self, agent_id: str) -> dict:
        """Get config for specific agent."""
        agents = self.config.get("agents", {})
        if agent_id in agents:
            return agents[agent_id]
        return agents.get("defaults", {})

    def _get_sandbox_mode(self) -> SandboxMode:
        """Get configured sandbox mode."""
        mode_str = (
            self.config.get("agents", {}).get("defaults", {}).get("sandbox", {}).get("mode", "off")
        )
        try:
            return SandboxMode(mode_str)
        except ValueError:
            return SandboxMode.OFF

    def _should_apply_sandbox(
        self,
        mode: SandboxMode,
        is_main_session: bool,
    ) -> bool:
        """Determine if sandbox should be applied."""
        if mode == SandboxMode.OFF:
            return False
        if mode == SandboxMode.ALL:
            return True
        if mode == SandboxMode.NON_MAIN:
            return not is_main_session
        return False

    def _get_sandbox_policy(self, agent_config: dict) -> ToolPolicy | None:
        """Get sandbox tool policy."""
        sandbox_tools = agent_config.get("sandbox", {}).get("tools", {})
        if sandbox_tools.get("allow") or sandbox_tools.get("deny"):
            return ToolPolicy(
                allow=sandbox_tools.get("allow"),
                deny=sandbox_tools.get("deny"),
            )
        return None


# ──────────────────────────────────────────────────────────────────────
# Predefined tool profiles (legacy compat + new TS-aligned profiles)
# ──────────────────────────────────────────────────────────────────────


def get_profile_policy(profile_name: str) -> ToolPolicy | None:
    """
    Get a predefined tool profile as a ToolPolicy.

    Supports both new TS-aligned profiles (minimal/coding/messaging/full)
    and legacy Python profiles (safe/restricted).
    """
    resolved = resolve_tool_profile_policy(profile_name)
    if resolved:
        return ToolPolicy(
            allow=expand_tool_groups(resolved.allow),
            deny=expand_tool_groups(resolved.deny),
        )
    # Legacy Python-only profiles
    legacy = _LEGACY_PROFILES.get(profile_name)
    return legacy


_LEGACY_PROFILES: dict[str, ToolPolicy] = {
    "safe": ToolPolicy(
        allow=["bash", "read_file", "write_file", "edit_file", "ls"],
        deny=["browser", "nodes"],
    ),
    "restricted": ToolPolicy(
        allow=["bash", "read_file"],
        deny=["write_file", "edit_file", "browser", "nodes"],
    ),
}
