"""
Session key resolution from various identifiers

This module implements session key resolution matching the TypeScript implementation.
Supports resolving sessions by:
- Direct session key
- Session ID (UUID)
- Label (user-defined name)
"""

import logging
from typing import Dict, Optional
from dataclasses import dataclass

from openclaw.agents.session_entry import SessionEntry
from openclaw.config.sessions.store import load_session_store
from openclaw.config.sessions.paths import get_default_store_path
from openclaw.gateway.session_utils import (
    SessionsListOptions,
    list_sessions_from_store,
    resolve_gateway_session_store_target,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class SessionResolveParams:
    """Parameters for session resolution"""
    # Exactly one of these must be provided
    key: Optional[str] = None
    session_id: Optional[str] = None
    label: Optional[str] = None
    
    # Optional filters
    include_global: bool = True
    include_unknown: bool = True
    agent_id: Optional[str] = None
    spawned_by: Optional[str] = None


@dataclass
class SessionResolveResult:
    """Result of session resolution"""
    ok: bool
    key: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Session Resolution
# ============================================================================

def resolve_session_key_from_resolve_params(
    params: SessionResolveParams,
    workspace_root: Optional[str] = None
) -> SessionResolveResult:
    """
    Resolve session key from one of: key, sessionId, or label
    
    Args:
        params: Resolution parameters
        workspace_root: Optional workspace root directory
        
    Returns:
        SessionResolveResult with resolved key or error
    """
    # Validate: exactly one identifier must be provided
    provided = sum([
        params.key is not None,
        params.session_id is not None,
        params.label is not None,
    ])
    
    if provided == 0:
        return SessionResolveResult(
            ok=False,
            error="Exactly one of key, sessionId, or label must be provided"
        )
    
    if provided > 1:
        return SessionResolveResult(
            ok=False,
            error="Only one of key, sessionId, or label can be provided"
        )
    
    # =========================================================================
    # 1. Resolve by key (direct lookup)
    # =========================================================================
    
    if params.key is not None:
        return _resolve_by_key(params)
    
    # =========================================================================
    # 2. Resolve by sessionId (UUID search)
    # =========================================================================
    
    if params.session_id is not None:
        return _resolve_by_session_id(params)
    
    # =========================================================================
    # 3. Resolve by label (label search)
    # =========================================================================
    
    if params.label is not None:
        return _resolve_by_label(params)
    
    return SessionResolveResult(
        ok=False,
        error="No valid identifier provided"
    )


def _resolve_by_key(params: SessionResolveParams) -> SessionResolveResult:
    """
    Resolve session by direct key lookup
    
    Args:
        params: Resolution parameters with key
        
    Returns:
        SessionResolveResult
    """
    key = params.key.strip() if params.key else ""
    
    if not key:
        return SessionResolveResult(ok=False, error="Empty key")
    
    # Resolve store target
    try:
        target = resolve_gateway_session_store_target(key, params.agent_id or "main")
        store = load_session_store(target.store_path)
        
        # Try to find entry
        entry = None
        for store_key in target.store_keys:
            if store_key in store:
                entry = store[store_key]
                break
        
        if not entry:
            return SessionResolveResult(
                ok=False,
                error=f"Session not found: {key}"
            )
        
        # Apply filters
        if not _entry_matches_filters(key, entry, params):
            return SessionResolveResult(
                ok=False,
                error=f"Session does not match filters: {key}"
            )
        
        return SessionResolveResult(ok=True, key=target.canonical_key)
        
    except Exception as e:
        logger.error(f"Failed to resolve by key '{key}': {e}")
        return SessionResolveResult(ok=False, error=str(e))


def _resolve_by_session_id(params: SessionResolveParams) -> SessionResolveResult:
    """
    Resolve session by sessionId (UUID) search
    
    Args:
        params: Resolution parameters with session_id
        
    Returns:
        SessionResolveResult
    """
    session_id = params.session_id.strip() if params.session_id else ""
    
    if not session_id:
        return SessionResolveResult(ok=False, error="Empty sessionId")
    
    # Load combined store (potentially from multiple agents)
    agent_ids = [params.agent_id] if params.agent_id else ["main"]
    
    matches: list[tuple[str, SessionEntry]] = []
    
    for agent_id in agent_ids:
        store_path = get_default_store_path(agent_id)
        try:
            store = load_session_store(str(store_path))
            
            # Search for matching session_id
            for key, entry in store.items():
                if entry.sessionId == session_id:
                    # Apply filters
                    if _entry_matches_filters(key, entry, params):
                        matches.append((key, entry))
            
        except Exception as e:
            logger.warning(f"Failed to load store for agent {agent_id}: {e}")
            continue
    
    if len(matches) == 0:
        return SessionResolveResult(
            ok=False,
            error=f"No session found with sessionId: {session_id}"
        )
    
    if len(matches) > 1:
        # Multiple matches - return error
        keys = [k for k, _ in matches]
        return SessionResolveResult(
            ok=False,
            error=f"Multiple sessions found with sessionId {session_id}: {keys}"
        )
    
    # Single match
    resolved_key, _ = matches[0]
    return SessionResolveResult(ok=True, key=resolved_key)


def _resolve_by_label(params: SessionResolveParams) -> SessionResolveResult:
    """
    Resolve session by label search
    
    Args:
        params: Resolution parameters with label
        
    Returns:
        SessionResolveResult
    """
    label = params.label.strip() if params.label else ""
    
    if not label:
        return SessionResolveResult(ok=False, error="Empty label")
    
    # Validate label length
    if len(label) > 64:
        return SessionResolveResult(
            ok=False,
            error="Label must be 64 characters or less"
        )
    
    # Load combined store
    agent_ids = [params.agent_id] if params.agent_id else ["main"]
    
    matches: list[tuple[str, SessionEntry]] = []
    
    for agent_id in agent_ids:
        store_path = get_default_store_path(agent_id)
        try:
            store = load_session_store(str(store_path))
            
            # Search for matching label
            for key, entry in store.items():
                if entry.label == label:
                    # Apply filters
                    if _entry_matches_filters(key, entry, params):
                        matches.append((key, entry))
            
        except Exception as e:
            logger.warning(f"Failed to load store for agent {agent_id}: {e}")
            continue
    
    if len(matches) == 0:
        return SessionResolveResult(
            ok=False,
            error=f"No session found with label: {label}"
        )
    
    if len(matches) > 1:
        # Multiple matches - return error
        keys = [k for k, _ in matches]
        return SessionResolveResult(
            ok=False,
            error=f"Multiple sessions found with label '{label}': {keys}"
        )
    
    # Single match
    resolved_key, _ = matches[0]
    return SessionResolveResult(ok=True, key=resolved_key)


def _entry_matches_filters(
    key: str,
    entry: SessionEntry,
    params: SessionResolveParams
) -> bool:
    """
    Check if entry matches optional filters
    
    Args:
        key: Session key
        entry: Session entry
        params: Resolution parameters with filters
        
    Returns:
        True if entry matches all filters
    """
    # Include global/unknown filters
    if key == "global" and not params.include_global:
        return False
    
    if key == "unknown" and not params.include_unknown:
        return False
    
    # Agent ID filter (already handled by store selection)
    
    # Spawned by filter
    if params.spawned_by is not None:
        if entry.spawnedBy != params.spawned_by:
            return False
    
    return True
