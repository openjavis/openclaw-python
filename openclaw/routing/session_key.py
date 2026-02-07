"""
Session key utilities

Matches TypeScript src/routing/session-key.ts

Session keys uniquely identify conversation contexts:
  - agent:main:main (default main session)
  - agent:main:dm:user123 (DM with user123)
  - agent:main:telegram:group:456 (Telegram group 456)
  - agent:main:discord:channel:789 (Discord channel 789)
"""

from __future__ import annotations

import re
from typing import NamedTuple

# Constants (matches TS lines 10-12)
DEFAULT_AGENT_ID = "main"
DEFAULT_MAIN_KEY = "main"
DEFAULT_ACCOUNT_ID = "default"

# Pre-compiled regex (matches TS lines 14-18)
VALID_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
INVALID_CHARS_RE = re.compile(r"[^a-z0-9_-]+")
LEADING_DASH_RE = re.compile(r"^-+")
TRAILING_DASH_RE = re.compile(r"-+$")


class ParsedAgentSessionKey(NamedTuple):
    """Parsed session key components."""

    agent_id: str
    rest: str
    full_key: str


def normalize_main_key(value: str | None) -> str:
    """Normalize main key (matches TS normalizeMainKey)."""
    trimmed = (value or "").strip()
    return trimmed.lower() if trimmed else DEFAULT_MAIN_KEY


def normalize_agent_id(value: str | None) -> str:
    """
    Normalize agent ID (matches TS normalizeAgentId lines 61-78).

    Rules:
    - Trim and lowercase
    - Must match /^[a-z0-9][a-z0-9_-]{0,63}$/i
    - If invalid: collapse invalid chars to "-", max 64 chars
    - Empty → DEFAULT_AGENT_ID

    Examples:
        "Main" → "main"
        "my Agent!" → "my-agent"
        "" → "main"
    """
    trimmed = (value or "").strip()
    if not trimmed:
        return DEFAULT_AGENT_ID

    # Already valid
    if VALID_ID_RE.match(trimmed):
        return trimmed.lower()

    # Best-effort fallback: collapse invalid characters to "-"
    normalized = INVALID_CHARS_RE.sub("-", trimmed.lower())
    normalized = LEADING_DASH_RE.sub("", normalized)
    normalized = TRAILING_DASH_RE.sub("", normalized)
    normalized = normalized[:64]

    return normalized if normalized else DEFAULT_AGENT_ID


def sanitize_agent_id(value: str | None) -> str:
    """
    Sanitize agent ID (matches TS sanitizeAgentId lines 81-96).

    Same rules as normalize_agent_id (in TS, they're identical).
    """
    return normalize_agent_id(value)


def normalize_account_id(value: str | None) -> str:
    """
    Normalize account ID (matches TS normalizeAccountId lines 99-114).

    Same validation as agent ID.

    Examples:
        "Account 1" → "account-1"
        "" → "default"
    """
    trimmed = (value or "").strip()
    if not trimmed:
        return DEFAULT_ACCOUNT_ID

    if VALID_ID_RE.match(trimmed):
        return trimmed.lower()

    normalized = INVALID_CHARS_RE.sub("-", trimmed.lower())
    normalized = LEADING_DASH_RE.sub("", normalized)
    normalized = TRAILING_DASH_RE.sub("", normalized)
    normalized = normalized[:64]

    return normalized if normalized else DEFAULT_ACCOUNT_ID


def build_agent_main_session_key(
    agent_id: str,
    main_key: str | None = None,
) -> str:
    """
    Build main session key (matches TS buildAgentMainSessionKey lines 117-123).

    Format: agent:<agentId>:<mainKey>

    Examples:
        ("main", None) → "agent:main:main"
        ("myagent", "prod") → "agent:myagent:prod"
    """
    normalized_agent = normalize_agent_id(agent_id)
    normalized_main = normalize_main_key(main_key)
    return f"agent:{normalized_agent}:{normalized_main}"


def build_agent_peer_session_key(
    agent_id: str,
    channel: str,
    peer_kind: str = "dm",
    peer_id: str | None = None,
    account_id: str | None = None,
    main_key: str | None = None,
    dm_scope: str = "main",
) -> str:
    """
    Build peer session key (simplified version matching TS buildAgentPeerSessionKey).

    DM scope modes:
    - "main": agent:<agentId>:main (all DMs share main session)
    - "per-peer": agent:<agentId>:dm:<peerId>
    - "per-channel-peer": agent:<agentId>:<channel>:dm:<peerId>
    - "per-account-channel-peer": agent:<agentId>:<channel>:<accountId>:dm:<peerId>

    For groups:
    - agent:<agentId>:<channel>:group:<groupId>

    For channels/rooms:
    - agent:<agentId>:<channel>:channel:<channelId>
    """
    normalized_agent = normalize_agent_id(agent_id)
    normalized_channel = channel.strip().lower() if channel else "unknown"
    normalized_peer_id = (peer_id or "").strip()

    # DM handling
    if peer_kind == "dm":
        if dm_scope == "main":
            return build_agent_main_session_key(agent_id, main_key)
        elif dm_scope == "per-peer":
            return f"agent:{normalized_agent}:dm:{normalized_peer_id}"
        elif dm_scope == "per-channel-peer":
            return f"agent:{normalized_agent}:{normalized_channel}:dm:{normalized_peer_id}"
        elif dm_scope == "per-account-channel-peer":
            normalized_account = normalize_account_id(account_id)
            return f"agent:{normalized_agent}:{normalized_channel}:{normalized_account}:dm:{normalized_peer_id}"

    # Group handling
    if peer_kind == "group":
        return f"agent:{normalized_agent}:{normalized_channel}:group:{normalized_peer_id}"

    # Channel/room handling
    if peer_kind == "channel":
        return f"agent:{normalized_agent}:{normalized_channel}:channel:{normalized_peer_id}"

    # Fallback
    return build_agent_main_session_key(agent_id, main_key)


def parse_agent_session_key(session_key: str | None) -> ParsedAgentSessionKey | None:
    """
    Parse session key into components (matches TS parseAgentSessionKey).

    Format: agent:<agentId>:<rest>

    Examples:
        "agent:main:main" → ParsedAgentSessionKey("main", "main", ...)
        "agent:myagent:telegram:group:123" → ParsedAgentSessionKey("myagent", "telegram:group:123", ...)
        "invalid" → None
    """
    raw = (session_key or "").strip()
    if not raw:
        return None

    if not raw.startswith("agent:"):
        return None

    # Split: agent:<agentId>:<rest>
    parts = raw.split(":", 2)
    if len(parts) < 3:
        return None

    agent_id = parts[1]
    rest = parts[2]

    return ParsedAgentSessionKey(
        agent_id=agent_id,
        rest=rest,
        full_key=raw,
    )


def resolve_agent_id_from_session_key(session_key: str | None) -> str:
    """Extract agent ID from session key (matches TS resolveAgentIdFromSessionKey lines 56-58)."""
    parsed = parse_agent_session_key(session_key)
    return normalize_agent_id(parsed.agent_id if parsed else None)


def to_agent_store_session_key(
    agent_id: str,
    request_key: str | None,
    main_key: str | None = None,
) -> str:
    """
    Convert request key to store key (matches TS toAgentStoreSessionKey lines 37-53).

    Args:
        agent_id: Agent identifier
        request_key: Request session key (may be partial)
        main_key: Main key override

    Returns:
        Full agent store session key
    """
    raw = (request_key or "").strip()

    if not raw or raw == DEFAULT_MAIN_KEY:
        return build_agent_main_session_key(agent_id, main_key)

    lowered = raw.lower()

    if lowered.startswith("agent:"):
        return lowered

    if lowered.startswith("subagent:"):
        return f"agent:{normalize_agent_id(agent_id)}:{lowered}"

    return f"agent:{normalize_agent_id(agent_id)}:{lowered}"


def to_agent_request_session_key(store_key: str | None) -> str | None:
    """
    Convert store key to request key (matches TS toAgentRequestSessionKey lines 29-34).

    Strips "agent:<agentId>:" prefix to get the rest.
    """
    raw = (store_key or "").strip()
    if not raw:
        return None

    parsed = parse_agent_session_key(raw)
    return parsed.rest if parsed else raw


def looks_like_session_key(value: str | None) -> bool:
    """Check if value looks like a session key."""
    raw = (value or "").strip()
    return raw.startswith("agent:") and ":" in raw[6:]


def is_subagent_session_key(session_key: str | None) -> bool:
    """Check if session key represents a subagent."""
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return False
    return parsed.rest.startswith("subagent:")


def is_acp_session_key(session_key: str | None) -> bool:
    """Check if session key is an ACP (Agent Control Protocol) session."""
    parsed = parse_agent_session_key(session_key)
    if not parsed:
        return False
    return parsed.rest.startswith("acp:")
