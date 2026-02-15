"""
Gateway API methods for session management

This module implements all sessions.* Gateway API methods matching the TypeScript implementation.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from openclaw.agents.session_entry import SessionEntry
from openclaw.config.sessions.store_utils import (
    load_session_store,
    update_session_store,
)
from openclaw.config.sessions.paths import get_default_store_path
from openclaw.config.sessions.transcripts import (
    read_session_preview_items,
    compact_transcript,
    delete_transcript,
    get_session_transcript_path,
)
from openclaw.gateway.session_utils import (
    SessionsListOptions,
    list_sessions_from_store,
    resolve_gateway_session_store_target,
    resolve_main_session_key,
)
from openclaw.gateway.sessions_resolve import (
    SessionResolveParams,
    resolve_session_key_from_resolve_params,
)
from openclaw.gateway.sessions_patch import apply_sessions_patch_to_store

logger = logging.getLogger(__name__)


# =============================================================================
# sessions.list
# =============================================================================

class SessionsListMethod:
    """List sessions with filtering and sorting"""
    
    name = "sessions.list"
    description = "List all sessions with optional filtering and sorting"
    category = "sessions"
    
    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute sessions.list
        
        Params:
        - agentId: Filter by agent ID
        - spawnedBy: Filter by parent session
        - label: Filter by label
        - search: Search query
        - includeGlobal: Include global session (default: true)
        - includeUnknown: Include unknown session (default: true)
        - activeMinutes: Filter by recent activity
        - addDerivedTitles: Add derived titles (default: false)
        - addLastMessagePreview: Add last message preview (default: false)
        - limit: Maximum results
        - offset: Skip first N results
        
        Returns:
        - SessionsListResult with sessions array
        """
        agent_id = params.get("agentId", "main")
        store_path = get_default_store_path(agent_id)
        
        try:
            store = load_session_store(str(store_path))
            
            opts = SessionsListOptions(
                agent_id=params.get("agentId"),
                spawned_by=params.get("spawnedBy"),
                label=params.get("label"),
                search=params.get("search"),
                include_global=params.get("includeGlobal", True),
                include_unknown=params.get("includeUnknown", True),
                active_minutes=params.get("activeMinutes"),
                add_derived_titles=params.get("addDerivedTitles", False),
                add_last_message_preview=params.get("addLastMessagePreview", False),
                limit=params.get("limit"),
                offset=params.get("offset", 0),
            )
            
            result = list_sessions_from_store(str(store_path), store, opts)
            
            # Convert to dict
            return {
                "ts": result.ts,
                "path": result.path,
                "count": result.count,
                "defaults": {
                    "modelProvider": result.defaults.model_provider,
                    "model": result.defaults.model,
                    "contextTokens": result.defaults.context_tokens,
                },
                "sessions": [
                    {
                        "key": row.key,
                        "kind": row.kind,
                        "label": row.label,
                        "displayName": row.display_name,
                        "derivedTitle": row.derived_title,
                        "lastMessagePreview": row.last_message_preview,
                        "channel": row.channel,
                        "subject": row.subject,
                        "groupChannel": row.group_channel,
                        "space": row.space,
                        "chatType": row.chat_type,
                        "origin": row.origin,
                        "updatedAt": row.updated_at,
                        "sessionId": row.session_id,
                        "systemSent": row.system_sent,
                        "abortedLastRun": row.aborted_last_run,
                        "thinkingLevel": row.thinking_level,
                        "verboseLevel": row.verbose_level,
                        "reasoningLevel": row.reasoning_level,
                        "elevatedLevel": row.elevated_level,
                        "sendPolicy": row.send_policy,
                        "inputTokens": row.input_tokens,
                        "outputTokens": row.output_tokens,
                        "totalTokens": row.total_tokens,
                        "responseUsage": row.response_usage,
                        "modelProvider": row.model_provider,
                        "model": row.model,
                        "contextTokens": row.context_tokens,
                        "deliveryContext": row.delivery_context,
                        "lastChannel": row.last_channel,
                        "lastTo": row.last_to,
                        "lastAccountId": row.last_account_id,
                    }
                    for row in result.sessions
                ]
            }
            
        except Exception as e:
            logger.error(f"sessions.list failed: {e}")
            raise
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "agentId": {"type": "string"},
                "spawnedBy": {"type": "string"},
                "label": {"type": "string"},
                "search": {"type": "string"},
                "includeGlobal": {"type": "boolean"},
                "includeUnknown": {"type": "boolean"},
                "activeMinutes": {"type": "integer"},
                "addDerivedTitles": {"type": "boolean"},
                "addLastMessagePreview": {"type": "boolean"},
                "limit": {"type": "integer"},
                "offset": {"type": "integer"},
            },
        }


# =============================================================================
# sessions.preview
# =============================================================================

class SessionsPreviewMethod:
    """Get transcript preview for sessions"""
    
    name = "sessions.preview"
    description = "Get transcript preview for multiple sessions"
    category = "sessions"
    
    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute sessions.preview
        
        Params:
        - keys: List of session keys (max 64)
        - limit: Messages per session (default: 12)
        - maxChars: Max characters per message (default: 240)
        
        Returns:
        - SessionsPreviewResult with previews array
        """
        keys_raw = params.get("keys", [])
        keys = [str(k).strip() for k in keys_raw if k][:64]
        
        limit = params.get("limit", 12)
        max_chars = params.get("maxChars", 240)
        
        if not keys:
            return {
                "ts": int(time.time() * 1000),
                "previews": []
            }
        
        previews = []
        
        for key in keys:
            try:
                target = resolve_gateway_session_store_target(key)
                store = load_session_store(target.store_path)
                
                # Find entry
                entry = None
                for store_key in target.store_keys:
                    if store_key in store:
                        entry = store[store_key]
                        break
                
                if not entry or not entry.session_id:
                    previews.append({"key": key, "status": "missing", "items": []})
                    continue
                
                # Read transcript preview
                items = read_session_preview_items(
                    entry.session_id,
                    target.store_path,
                    entry.session_file,
                    limit=limit,
                    max_chars=max_chars
                )
                
                previews.append({
                    "key": key,
                    "status": "ok" if items else "empty",
                    "items": [{"role": item.role, "text": item.text} for item in items]
                })
                
            except Exception as e:
                logger.error(f"Failed to preview session {key}: {e}")
                previews.append({"key": key, "status": "error", "items": []})
        
        return {
            "ts": int(time.time() * 1000),
            "previews": previews
        }
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
                "maxChars": {"type": "integer"},
            },
            "required": ["keys"],
        }


# =============================================================================
# sessions.resolve
# =============================================================================

class SessionsResolveMethod:
    """Resolve session key from identifier"""
    
    name = "sessions.resolve"
    description = "Resolve session key from key/sessionId/label"
    category = "sessions"
    
    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute sessions.resolve
        
        Params (exactly one required):
        - key: Direct session key
        - sessionId: UUID to search
        - label: Label to search
        
        Optional filters:
        - includeGlobal, includeUnknown
        - agentId, spawnedBy
        
        Returns:
        - { ok: true, key: str } or { ok: false, error: str }
        """
        resolve_params = SessionResolveParams(
            key=params.get("key"),
            session_id=params.get("sessionId"),
            label=params.get("label"),
            include_global=params.get("includeGlobal", True),
            include_unknown=params.get("includeUnknown", True),
            agent_id=params.get("agentId"),
            spawned_by=params.get("spawnedBy"),
        )
        
        result = resolve_session_key_from_resolve_params(resolve_params)
        
        if result.ok:
            return {"ok": True, "key": result.key}
        else:
            return {"ok": False, "error": result.error}
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "sessionId": {"type": "string"},
                "label": {"type": "string"},
                "includeGlobal": {"type": "boolean"},
                "includeUnknown": {"type": "boolean"},
                "agentId": {"type": "string"},
                "spawnedBy": {"type": "string"},
            },
        }


# =============================================================================
# sessions.patch
# =============================================================================

class SessionsPatchMethod:
    """Update session entry fields"""
    
    name = "sessions.patch"
    description = "Update session entry fields with validation"
    category = "sessions"
    
    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute sessions.patch
        
        Params:
        - key: Session key (required)
        - patch: Partial SessionEntry to merge
        
        Returns:
        - SessionsPatchResult with updated entry
        """
        key = params.get("key")
        if not key:
            raise ValueError("key is required")
        
        patch = params.get("patch", {})
        
        target = resolve_gateway_session_store_target(key)
        
        def mutator(store: Dict[str, SessionEntry]) -> None:
            apply_sessions_patch_to_store(
                store,
                target.canonical_key,
                patch,
                model_catalog=None
            )
        
        update_session_store(target.store_path, mutator)
        
        # Reload to get updated entry
        store = load_session_store(target.store_path)
        entry = store[target.canonical_key]
        
        return {
            "ok": True,
            "path": target.store_path,
            "key": target.canonical_key,
            "entry": entry.model_dump(exclude_none=False),
        }
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "patch": {"type": "object"},
            },
            "required": ["key", "patch"],
        }


# =============================================================================
# sessions.reset
# =============================================================================

class SessionsResetMethod:
    """Reset session with new UUID, preserve config"""
    
    name = "sessions.reset"
    description = "Reset session with new UUID while preserving configuration"
    category = "sessions"
    
    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute sessions.reset
        
        Params:
        - key: Session key (required)
        - archiveTranscript: Archive before deleting (default: true)
        
        Returns:
        - { ok: true, key: str, sessionId: str }
        """
        key = params.get("key")
        if not key:
            raise ValueError("key is required")
        
        archive_transcript = params.get("archiveTranscript", True)
        
        target = resolve_gateway_session_store_target(key)
        new_session_id = str(uuid.uuid4())
        now_ms = int(time.time() * 1000)
        
        # Get old session ID before reset
        old_session_id = None
        store_data = load_session_store(target.store_path)
        entry = store_data.get(target.canonical_key)
        if entry:
            old_session_id = entry.session_id
        
        def mutator(store: Dict[str, SessionEntry]) -> None:
            entry = store.get(target.canonical_key)
            
            # If session doesn't exist yet, create a new one (graceful handling)
            if not entry:
                logger.info(f"Session not found for reset, creating new session: {key}")
                reset_entry = SessionEntry(
                    session_id=new_session_id,
                    updated_at=now_ms
                )
                store[target.canonical_key] = reset_entry
                return
            
            # Preserve configuration fields from existing session
            preserved = {
                "thinking_level": entry.thinking_level,
                "verbose_level": entry.verbose_level,
                "reasoning_level": entry.reasoning_level,
                "elevated_level": entry.elevated_level,
                "label": entry.label,
                "display_name": entry.display_name,
                "provider_override": entry.provider_override,
                "model_override": entry.model_override,
                "exec_host": entry.exec_host,
                "exec_security": entry.exec_security,
                "exec_ask": entry.exec_ask,
                "exec_node": entry.exec_node,
                "send_policy": entry.send_policy,
                "group_activation": entry.group_activation,
                "response_usage": entry.response_usage,
                "origin": entry.origin,
                "delivery_context": entry.delivery_context,
            }
            
            # Create new entry with reset fields
            reset_entry = SessionEntry(
                session_id=new_session_id,
                updated_at=now_ms,
                **{k: v for k, v in preserved.items() if v is not None}
            )
            
            store[target.canonical_key] = reset_entry
        
        update_session_store(target.store_path, mutator)
        
        # Delete old transcript
        if old_session_id:
            try:
                # Archive transcript if requested (by renaming with timestamp)
                if archive_transcript:
                    transcript_path = get_session_transcript_path(target.canonical_key)
                    if transcript_path.exists():
                        archive_name = f"{transcript_path.stem}_reset_{now_ms}{transcript_path.suffix}"
                        archive_path = transcript_path.parent / archive_name
                        transcript_path.rename(archive_path)
                        logger.info(f"Archived transcript to {archive_path}")
                else:
                    # Delete transcript directly
                    deleted = delete_transcript(target.canonical_key)
                    if deleted:
                        logger.info(f"Deleted transcript for {target.canonical_key}")
            except Exception as e:
                logger.warning(f"Failed to delete transcript for {target.canonical_key}: {e}")
        
        return {
            "ok": True,
            "key": target.canonical_key,
            "sessionId": new_session_id
        }
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
            },
            "required": ["key"],
        }


# =============================================================================
# sessions.delete
# =============================================================================

class SessionsDeleteMethod:
    """Delete session with protection"""
    
    name = "sessions.delete"
    description = "Delete session with main session protection"
    category = "sessions"
    
    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute sessions.delete
        
        Params:
        - key: Session key (required)
        - archiveTranscript: Archive before deleting (default: true)
        
        Returns:
        - { ok: true, deleted: bool }
        """
        key = params.get("key")
        if not key:
            raise ValueError("key is required")
        
        archive_transcript = params.get("archiveTranscript", True)
        
        target = resolve_gateway_session_store_target(key)
        
        # Check if this is the main session
        main_key = resolve_main_session_key(target.agent_id)
        if target.canonical_key == main_key:
            raise ValueError("Cannot delete main session")
        
        # Delete transcript
        store = load_session_store(target.store_path)
        entry = store.get(target.canonical_key)
        
        if entry and entry.session_id:
            delete_transcript(
                entry.session_id,
                target.store_path,
                entry.session_file,
                archive_first=archive_transcript,
                archive_reason="delete"
            )
        
        # Delete from store
        def mutator(store_dict: Dict[str, SessionEntry]) -> None:
            if target.canonical_key in store_dict:
                del store_dict[target.canonical_key]
        
        update_session_store(target.store_path, mutator)
        
        return {"ok": True, "deleted": True}
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "archiveTranscript": {"type": "boolean"},
            },
            "required": ["key"],
        }


# =============================================================================
# sessions.compact
# =============================================================================

class SessionsCompactMethod:
    """Compact session transcript"""
    
    name = "sessions.compact"
    description = "Compact session transcript by keeping last N lines"
    category = "sessions"
    
    async def execute(self, connection: Any, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute sessions.compact
        
        Params:
        - key: Session key (required)
        - maxLines: Keep last N lines (required)
        
        Returns:
        - { ok: true, removedLines: int, keptLines: int, archivedPath: str }
        """
        key = params.get("key")
        if not key:
            raise ValueError("key is required")
        
        max_lines = params.get("maxLines")
        if max_lines is None:
            raise ValueError("maxLines is required")
        
        target = resolve_gateway_session_store_target(key)
        store = load_session_store(target.store_path)
        entry = store.get(target.canonical_key)
        
        if not entry or not entry.session_id:
            raise ValueError(f"Session not found: {key}")
        
        # Compact transcript
        result = compact_transcript(
            entry.session_id,
            target.store_path,
            keep_lines=max_lines,
            session_file=entry.session_file,
            archive_reason="compaction"
        )
        
        # Update store: clear token counts, increment compaction count
        def mutator(store_dict: Dict[str, SessionEntry]) -> None:
            if target.canonical_key in store_dict:
                e = store_dict[target.canonical_key]
                e.input_tokens = None
                e.output_tokens = None
                e.total_tokens = None
                e.compaction_count = (e.compaction_count or 0) + 1
                e.updated_at = int(time.time() * 1000)
        
        update_session_store(target.store_path, mutator)
        
        return {
            "ok": True,
            "removedLines": result["removed_lines"],
            "keptLines": result["kept_lines"],
            "archivedPath": result["archived_path"],
        }
    
    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "maxLines": {"type": "integer"},
            },
            "required": ["key", "maxLines"],
        }
