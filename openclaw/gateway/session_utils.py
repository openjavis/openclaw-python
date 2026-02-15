"""
Session utilities for gateway operations

This module provides utility functions for session resolution, listing,
classification, and title derivation matching the TypeScript implementation.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, NamedTuple
from dataclasses import dataclass

from openclaw.agents.session_entry import SessionEntry
from openclaw.config.sessions.store import load_session_store
from openclaw.config.sessions.paths import (
    get_default_store_path,
    resolve_session_store_path,
)
from openclaw.config.sessions.transcripts import (
    read_first_user_message,
    read_last_message_preview,
    read_transcript_preview,
)
from openclaw.routing.session_key import (
    parse_agent_session_key,
    normalize_agent_id,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class GatewaySessionsDefaults:
    """Default values for sessions"""
    model_provider: Optional[str]
    model: Optional[str]
    context_tokens: Optional[int]


@dataclass
class GatewaySessionRow:
    """Session row for gateway list response"""
    key: str
    kind: Literal["direct", "group", "global", "unknown"]
    label: Optional[str] = None
    display_name: Optional[str] = None
    derived_title: Optional[str] = None
    last_message_preview: Optional[str] = None
    channel: Optional[str] = None
    subject: Optional[str] = None
    group_channel: Optional[str] = None
    space: Optional[str] = None
    chat_type: Optional[str] = None
    origin: Optional[Dict[str, Any]] = None
    updated_at: Optional[int] = None
    session_id: Optional[str] = None
    system_sent: Optional[bool] = None
    aborted_last_run: Optional[bool] = None
    thinking_level: Optional[str] = None
    verbose_level: Optional[str] = None
    reasoning_level: Optional[str] = None
    elevated_level: Optional[str] = None
    send_policy: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    response_usage: Optional[str] = None
    model_provider: Optional[str] = None
    model: Optional[str] = None
    context_tokens: Optional[int] = None
    delivery_context: Optional[Dict[str, Any]] = None
    last_channel: Optional[str] = None
    last_to: Optional[str] = None
    last_account_id: Optional[str] = None


@dataclass
class SessionsListResult:
    """Result of sessions.list operation"""
    ts: int
    path: str
    count: int
    defaults: GatewaySessionsDefaults
    sessions: List[GatewaySessionRow]


@dataclass
class GatewayStoreTarget:
    """Target store information for a session key"""
    agent_id: str
    store_path: str
    canonical_key: str
    store_keys: List[str]  # Alternative keys to check


class LoadedSessionEntry(NamedTuple):
    """Loaded session entry with context"""
    entry: SessionEntry
    store_path: str
    canonical_key: str
    store: Dict[str, SessionEntry]


# ============================================================================
# Session Key Resolution
# ============================================================================

def resolve_session_store_key(session_key: str, main_key: str = "main") -> str:
    """
    Resolve and canonicalize session key
    
    Args:
        session_key: Raw session key
        main_key: Main session key (default: "main")
        
    Returns:
        Canonical session key
    """
    key = session_key.strip()
    
    # Special keys pass through
    if key in ("global", "unknown"):
        return key
    
    # Parse agent session key
    parsed = parse_agent_session_key(key)
    if parsed:
        agent_id = parsed.agent_id
        rest = parsed.rest
        
        # Canonicalize "main" alias
        if rest == "main" or rest == main_key:
            return f"agent:{agent_id}:main"
        
        return f"agent:{agent_id}:{rest}"
    
    # Treat as simple key
    return key


def resolve_main_session_key(agent_id: str = "main", main_key: str = "main") -> str:
    """
    Resolve main session key for an agent
    
    Args:
        agent_id: Agent identifier
        main_key: Main session key name
        
    Returns:
        Main session key: agent:{agentId}:main
    """
    normalized_agent_id = normalize_agent_id(agent_id)
    return f"agent:{normalized_agent_id}:main"


def resolve_gateway_session_store_target(
    key: str,
    agent_id: str = "main",
    workspace_root: Optional[Path] = None
) -> GatewayStoreTarget:
    """
    Resolve store path and canonical key for a session
    
    Args:
        key: Session key
        agent_id: Default agent ID
        workspace_root: Workspace root directory
        
    Returns:
        GatewayStoreTarget with store information
    """
    # Parse agent from key
    parsed = parse_agent_session_key(key)
    if parsed:
        target_agent_id = parsed.agent_id
    else:
        target_agent_id = agent_id
    
    # Resolve store path
    store_path = get_default_store_path(target_agent_id)
    
    # Canonical key
    canonical_key = resolve_session_store_key(key)
    
    # Alternative keys to check (for migration)
    store_keys = [canonical_key]
    
    return GatewayStoreTarget(
        agent_id=target_agent_id,
        store_path=str(store_path),
        canonical_key=canonical_key,
        store_keys=store_keys
    )


# ============================================================================
# Session Loading
# ============================================================================

def load_session_entry(
    session_key: str,
    agent_id: str = "main",
    workspace_root: Optional[Path] = None
) -> Optional[LoadedSessionEntry]:
    """
    Load complete session entry with store context
    
    Args:
        session_key: Session key to load
        agent_id: Default agent ID
        workspace_root: Workspace root directory
        
    Returns:
        LoadedSessionEntry or None if not found
    """
    target = resolve_gateway_session_store_target(session_key, agent_id, workspace_root)
    store = load_session_store(target.store_path)
    
    # Try to find entry with alternative keys
    entry = None
    for key in target.store_keys:
        if key in store:
            entry = store[key]
            break
    
    if not entry:
        return None
    
    return LoadedSessionEntry(
        entry=entry,
        store_path=target.store_path,
        canonical_key=target.canonical_key,
        store=store
    )


def load_combined_session_store(
    agent_ids: Optional[List[str]] = None,
    workspace_root: Optional[Path] = None
) -> Dict[str, SessionEntry]:
    """
    Load and merge session stores from multiple agents
    
    Args:
        agent_ids: List of agent IDs to load (default: ["main"])
        workspace_root: Workspace root directory
        
    Returns:
        Combined store dictionary
    """
    if agent_ids is None:
        agent_ids = ["main"]
    
    combined: Dict[str, SessionEntry] = {}
    
    for agent_id in agent_ids:
        store_path = get_default_store_path(agent_id)
        if not Path(store_path).exists():
            continue
        
        store = load_session_store(str(store_path))
        
        # Merge with conflict resolution (latest updatedAt wins)
        for key, entry in store.items():
            if key not in combined or entry.updatedAt > combined[key].updatedAt:
                combined[key] = entry
    
    return combined


# ============================================================================
# Session Classification
# ============================================================================

def classify_session_key(key: str, entry: Optional[SessionEntry] = None) -> Literal["direct", "group", "global", "unknown"]:
    """
    Classify session by key pattern
    
    Args:
        key: Session key
        entry: Optional session entry for additional context
        
    Returns:
        Session kind: direct, group, global, or unknown
    """
    if key == "global":
        return "global"
    
    if key == "unknown":
        return "unknown"
    
    # Parse agent session key
    parsed = parse_agent_session_key(key)
    if not parsed:
        return "unknown"
    
    rest = parsed.rest
    
    # Group patterns
    if "group" in rest or "channel" in rest:
        return "group"
    
    # Check entry for group indicators
    if entry:
        if entry.chatType in ("group", "channel", "supergroup"):
            return "group"
        if entry.groupId or entry.groupChannel:
            return "group"
    
    # Default to direct
    return "direct"


# ============================================================================
# Session Title Derivation
# ============================================================================

def derive_session_title(
    entry: SessionEntry,
    first_user_message: Optional[str] = None
) -> str:
    """
    Derive display title for session
    
    Priority:
    1. displayName
    2. subject
    3. first user message
    4. sessionId (first 8 chars)
    
    Args:
        entry: Session entry
        first_user_message: Optional first user message
        
    Returns:
        Derived title
    """
    # 1. Display name
    if entry.displayName:
        return entry.displayName
    
    # 2. Subject
    if entry.subject:
        return entry.subject
    
    # 3. First user message
    if first_user_message:
        # Truncate to reasonable length
        if len(first_user_message) > 50:
            return first_user_message[:50] + "..."
        return first_user_message
    
    # 4. Session ID prefix
    return entry.sessionId[:8]


# ============================================================================
# Session Listing
# ============================================================================

@dataclass
class SessionsListOptions:
    """Options for listing sessions"""
    agent_id: Optional[str] = None
    spawned_by: Optional[str] = None
    label: Optional[str] = None
    search: Optional[str] = None
    include_global: bool = True
    include_unknown: bool = True
    active_minutes: Optional[int] = None
    add_derived_titles: bool = False
    add_last_message_preview: bool = False
    limit: Optional[int] = None
    offset: int = 0


def list_sessions_from_store(
    store_path: str,
    store: Dict[str, SessionEntry],
    opts: Optional[SessionsListOptions] = None
) -> SessionsListResult:
    """
    Filter, search, and sort sessions from store
    
    Args:
        store_path: Path to sessions.json
        store: Session store dictionary
        opts: List options
        
    Returns:
        SessionsListResult with filtered and sorted sessions
    """
    if opts is None:
        opts = SessionsListOptions()
    
    # Filter sessions
    filtered_sessions: List[tuple[str, SessionEntry]] = []
    
    for key, entry in store.items():
        # Agent ID filter
        if opts.agent_id:
            parsed = parse_agent_session_key(key)
            if not parsed or parsed.agent_id != opts.agent_id:
                continue
        
        # Spawned by filter
        if opts.spawned_by and entry.spawnedBy != opts.spawned_by:
            continue
        
        # Label filter
        if opts.label and entry.label != opts.label:
            continue
        
        # Search filter (case-insensitive)
        if opts.search:
            search_lower = opts.search.lower()
            searchable = " ".join([
                entry.sessionId,
                entry.label or "",
                entry.displayName or "",
                entry.subject or "",
                key,
            ]).lower()
            if search_lower not in searchable:
                continue
        
        # Include global/unknown
        if key == "global" and not opts.include_global:
            continue
        if key == "unknown" and not opts.include_unknown:
            continue
        
        # Active minutes filter
        if opts.active_minutes:
            now_ms = int(time.time() * 1000)
            cutoff_ms = now_ms - (opts.active_minutes * 60 * 1000)
            if entry.updatedAt < cutoff_ms:
                continue
        
        filtered_sessions.append((key, entry))
    
    # Sort by updatedAt (newest first)
    filtered_sessions.sort(key=lambda x: x[1].updatedAt, reverse=True)
    
    # Apply offset and limit
    if opts.offset and opts.offset > 0:
        filtered_sessions = filtered_sessions[opts.offset:]
    if opts.limit:
        filtered_sessions = filtered_sessions[:opts.limit]
    
    # Convert to GatewaySessionRow
    rows: List[GatewaySessionRow] = []
    for key, entry in filtered_sessions:
        kind = classify_session_key(key, entry)
        
        # Optionally add derived title
        derived_title = None
        if opts.add_derived_titles:
            first_message = None
            if entry.sessionFile or entry.sessionId:
                first_message = read_first_user_message(
                    entry.sessionId,
                    store_path,
                    entry.sessionFile
                )
            derived_title = derive_session_title(entry, first_message)
        
        # Optionally add last message preview
        last_message_preview = None
        if opts.add_last_message_preview:
            if entry.sessionFile or entry.sessionId:
                last_message_preview = read_last_message_preview(
                    entry.sessionId,
                    store_path,
                    entry.sessionFile
                )
        
        row = GatewaySessionRow(
            key=key,
            kind=kind,
            label=entry.label,
            display_name=entry.displayName,
            derived_title=derived_title,
            last_message_preview=last_message_preview,
            channel=entry.channel,
            subject=entry.subject,
            group_channel=entry.groupChannel,
            space=entry.space,
            chat_type=entry.chatType,
            origin=entry.origin.model_dump() if entry.origin else None,
            updated_at=entry.updatedAt,
            session_id=entry.sessionId,
            system_sent=entry.systemSent,
            aborted_last_run=entry.abortedLastRun,
            thinking_level=entry.thinkingLevel,
            verbose_level=entry.verboseLevel,
            reasoning_level=entry.reasoningLevel,
            elevated_level=entry.elevatedLevel,
            send_policy=entry.sendPolicy,
            input_tokens=entry.inputTokens,
            output_tokens=entry.outputTokens,
            total_tokens=entry.totalTokens,
            response_usage=entry.responseUsage,
            model_provider=entry.modelProvider,
            model=entry.model,
            context_tokens=entry.contextTokens,
            delivery_context=entry.deliveryContext.model_dump() if entry.deliveryContext else None,
            last_channel=entry.lastChannel,
            last_to=entry.lastTo,
            last_account_id=entry.lastAccountId,
        )
        rows.append(row)
    
    # Compute defaults (from first entry or None)
    defaults = GatewaySessionsDefaults(
        model_provider=rows[0].model_provider if rows else None,
        model=rows[0].model if rows else None,
        context_tokens=rows[0].context_tokens if rows else None,
    )
    
    return SessionsListResult(
        ts=int(time.time() * 1000),
        path=store_path,
        count=len(rows),
        defaults=defaults,
        sessions=rows
    )


# ============================================================================
# Session Preview Items
# ============================================================================

@dataclass
class SessionPreviewItem:
    """Preview item for session transcript"""
    role: Literal["user", "assistant", "tool", "system", "other"]
    text: str


def read_session_preview_items(
    session_id: str,
    store_path: str,
    session_file: Optional[str] = None,
    limit: int = 12,
    max_chars: int = 240
) -> List[SessionPreviewItem]:
    """
    Read session preview items from transcript
    
    Args:
        session_id: Session identifier
        store_path: Path to sessions.json
        session_file: Optional session file path
        limit: Number of messages to preview
        max_chars: Maximum characters per message
        
    Returns:
        List of preview items
    """
    messages = read_transcript_preview(
        session_id,
        store_path,
        session_file,
        limit=limit,
        max_chars=max_chars
    )
    
    items: List[SessionPreviewItem] = []
    for msg in messages:
        role = msg.get("role", "other")
        if role not in ("user", "assistant", "tool", "system"):
            role = "other"
        
        text = msg.get("content", "")
        items.append(SessionPreviewItem(role=role, text=text))
    
    return items
