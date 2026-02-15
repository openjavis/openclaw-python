"""
Session management for agent conversations
"""
from __future__ import annotations


import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from openclaw.agents.session_ids import generate_session_id, looks_like_session_id
from openclaw.agents.session_entry import SessionEntry, SessionStore
from openclaw.routing.session_key import (
    build_agent_main_session_key,
    build_agent_peer_session_key,
    normalize_agent_id,
    parse_agent_session_key,
)

logger = logging.getLogger(__name__)

# Cache TTL in seconds (matches TypeScript 45s)
SESSION_STORE_CACHE_TTL = 45.0


class Message(BaseModel):
    """A single message in a conversation"""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None  # For tool results
    images: list[str] | None = None  # Image URLs or paths

    def to_api_format(self) -> dict[str, Any]:
        """Convert to API format for LLM calls"""
        msg = {"role": self.role, "content": self.content}

        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id

        if self.name:
            msg["name"] = self.name

        return msg


class Session(BaseModel):
    """
    Manages a conversation session with persistence
    """

    session_id: str
    workspace_dir: Path
    session_key: str | None = None  # Optional session key for reference
    messages: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        session_id: str,
        workspace_dir: Path,
        session_key: str | None = None,
        **kwargs
    ):
        """
        Initialize session with UUID.
        
        Args:
            session_id: Session UUID (NOT session key)
            workspace_dir: Workspace directory
            session_key: Optional session key for reference (e.g., "agent:main:telegram:dm:123")
        """
        super().__init__(session_id=session_id, workspace_dir=workspace_dir, session_key=session_key, **kwargs)
        
        # Validate UUID format
        import uuid as uuid_module
        try:
            uuid_module.UUID(session_id)
        except ValueError:
            logger.warning(f"session_id is not a valid UUID: {session_id}")
        
        # Create sessions directory
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing session if exists
        if self._session_file.exists() and not self.messages:
            self._load()

    @property
    def _sessions_dir(self) -> Path:
        """
        Get sessions directory using OpenClaw standard path.
        
        Uses ~/.openclaw/agents/{agentId}/sessions/ format
        """
        home = Path.home()
        openclaw_home = home / ".openclaw"
        
        # Extract agent ID from session_key if available, else use "main"
        agent_id = "main"
        if hasattr(self, 'session_key') and self.session_key:
            from openclaw.routing.session_key import parse_agent_session_key
            parsed = parse_agent_session_key(self.session_key)
            if parsed and parsed.agent_id:
                agent_id = parsed.agent_id
        
        sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        
        return sessions_dir

    @property
    def _session_file(self) -> Path:
        """
        Get session file path using UUID.
        
        Format: ~/.openclaw/agents/{agentId}/sessions/{uuid}.json
        """
        return self._sessions_dir / f"{self.session_id}.json"

    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """Add a message to the session"""
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return msg

    def add_user_message(self, content: str) -> Message:
        """Add a user message"""
        return self.add_message("user", content)

    def add_assistant_message(
        self, content: str, tool_calls: list[dict[str, Any]] | None = None
    ) -> Message:
        """Add an assistant message"""
        return self.add_message("assistant", content, tool_calls=tool_calls)

    def add_system_message(self, content: str) -> Message:
        """Add a system message"""
        return self.add_message("system", content)

    def add_tool_message(self, tool_call_id: str, content: str, name: str | None = None) -> Message:
        """Add a tool result message"""
        return self.add_message("tool", content, tool_call_id=tool_call_id, name=name)

    def get_messages(self, limit: int | None = None) -> list[Message]:
        """Get messages, optionally limited to last N"""
        if limit is None:
            return self.messages
        return self.messages[-limit:]

    def get_messages_for_api(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get messages in API format"""
        messages = self.get_messages(limit)
        return [msg.to_api_format() for msg in messages]

    def clear(self) -> None:
        """Clear all messages"""
        self.messages = []
        self.updated_at = datetime.utcnow().isoformat()
        self._save()

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        self.metadata[key] = value
        self._save()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        return self.metadata.get(key, default)

    def _save(self) -> None:
        """Save session to disk"""
        try:
            data = {
                "session_id": self.session_id,
                "messages": [msg.model_dump() for msg in self.messages],
                "metadata": self.metadata,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
            }
            with open(self._session_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def _load(self) -> None:
        """Load session from disk"""
        try:
            with open(self._session_file) as f:
                data = json.load(f)

            self.messages = [Message(**msg) for msg in data.get("messages", [])]
            self.metadata = data.get("metadata", {})
            self.created_at = data.get("created_at", self.created_at)
            self.updated_at = data.get("updated_at", self.updated_at)
        except Exception as e:
            logger.error(f"Failed to load session: {e}")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sessionId": self.session_id,
            "messageCount": len(self.messages),
            "messages": [msg.model_dump() for msg in self.messages],
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


class SessionManager:
    """
    Manages multiple sessions with enhanced session key support
    
    New features:
    - Session key format (agent:id:channel:group:id)
    - UUID v4 session IDs with validation
    - DM scope modes (main, per-peer, per-channel-peer, per-account-channel-peer)
    - Agent ID normalization
    - Session key to session ID mapping
    """

    def __init__(self, workspace_dir: Path, agent_id: str = "main"):
        """
        Initialize session manager

        Args:
            workspace_dir: Base directory for session storage (legacy, still used for fallback)
            agent_id: Agent identifier (default: "main")
        """
        self.workspace_dir = Path(workspace_dir)
        self.agent_id = normalize_agent_id(agent_id)
        self._sessions: dict[str, Session] = {}

        # Create workspace directory (legacy)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # New OpenClaw standard path: ~/.openclaw/agents/{agentId}/sessions/
        openclaw_home = Path.home() / ".openclaw"
        self._sessions_dir = openclaw_home / "agents" / self.agent_id / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Support both old (session_map.json) and new (sessions.json) formats
        self._sessions_file = self._sessions_dir / "sessions.json"
        self._legacy_session_map_file = self._sessions_dir / "session_map.json"
        
        # Also check old workspace location for migration
        self._legacy_sessions_dir = self.workspace_dir / ".sessions"
        self._legacy_sessions_file = self._legacy_sessions_dir / "sessions.json"
        self._legacy_legacy_map_file = self._legacy_sessions_dir / "session_map.json"
        
        # Session store caching with mtime-based invalidation
        self._session_store: SessionStore | None = None
        self._session_store_loaded_at: float = 0.0
        self._session_store_file_mtime: float | None = None
        
        # Lock file for concurrent access protection
        self._lock_file = self._sessions_file.with_suffix(".json.lock")
        
        # Load initial session store
        self._session_store = self._load_session_store()
    
    @property
    def sessions_dir(self) -> Path:
        """Public accessor for sessions directory"""
        return self._sessions_dir
    
    def _acquire_lock(self, timeout: float = 10.0) -> bool:
        """
        Acquire file lock for session store access.
        
        Args:
            timeout: Maximum time to wait for lock (seconds)
            
        Returns:
            True if lock acquired
        """
        start_time = time.time()
        
        while True:
            try:
                # Try to create lock file exclusively
                self._lock_file.touch(exist_ok=False)
                logger.debug("Acquired session store lock")
                return True
            except FileExistsError:
                # Lock file exists - check if it's stale (>30s old)
                try:
                    lock_age = time.time() - self._lock_file.stat().st_mtime
                    if lock_age > 30.0:
                        # Stale lock - remove and retry
                        logger.warning(f"Removing stale lock file (age={lock_age:.1f}s)")
                        self._lock_file.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    # Lock was removed between check and stat
                    continue
                
                # Check timeout
                if time.time() - start_time > timeout:
                    logger.error(f"Failed to acquire lock after {timeout}s")
                    return False
                
                # Wait and retry
                time.sleep(0.1)
    
    def _release_lock(self) -> None:
        """Release file lock."""
        try:
            self._lock_file.unlink(missing_ok=True)
            logger.debug("Released session store lock")
        except Exception as e:
            logger.warning(f"Failed to release lock: {e}")
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached session store is still valid.
        
        Validates based on:
        1. Time since last load (45s TTL)
        2. File modification time
        
        Returns:
            True if cache is valid
        """
        if self._session_store is None:
            return False
        
        # Check TTL
        age = time.time() - self._session_store_loaded_at
        if age > SESSION_STORE_CACHE_TTL:
            logger.debug(f"Cache expired (age={age:.1f}s > TTL={SESSION_STORE_CACHE_TTL}s)")
            return False
        
        # Check file mtime
        if self._sessions_file.exists():
            try:
                current_mtime = self._sessions_file.stat().st_mtime
                if self._session_store_file_mtime is None or current_mtime != self._session_store_file_mtime:
                    logger.debug("Cache invalidated by file modification")
                    return False
            except OSError as e:
                logger.warning(f"Failed to check file mtime: {e}")
                return False
        
        return True
    
    def _get_session_store(self) -> SessionStore:
        """
        Get session store with caching.
        
        Returns:
            SessionStore instance
        """
        # Check cache validity
        if self._is_cache_valid():
            return self._session_store
        
        # Reload from disk
        logger.debug("Reloading session store from disk")
        if not self._acquire_lock(timeout=10.0):
            logger.warning("Failed to acquire lock, using stale cache")
            return self._session_store or SessionStore(__root__={})
        
        try:
            self._session_store = self._load_session_store()
            return self._session_store
        finally:
            self._release_lock()

    def _load_session_store(self) -> SessionStore:
        """Load session store, migrating from legacy formats and locations if needed."""
        # Update cache metadata
        self._session_store_loaded_at = time.time()
        
        # Try loading new format from new location first
        if self._sessions_file.exists():
            try:
                # Record file mtime
                self._session_store_file_mtime = self._sessions_file.stat().st_mtime
                
                with open(self._sessions_file) as f:
                    data = json.load(f)
                logger.info(f"Loaded sessions.json from {self._sessions_file}")
                return SessionStore.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load sessions.json: {e}")
        
        # Check old location for sessions.json
        if hasattr(self, '_legacy_sessions_file') and self._legacy_sessions_file.exists():
            try:
                logger.info(f"Migrating sessions.json from {self._legacy_sessions_file} to {self._sessions_file}")
                with open(self._legacy_sessions_file) as f:
                    data = json.load(f)
                store = SessionStore.from_dict(data)
                # Save to new location
                self._save_session_store(store)
                logger.info(f"Migrated sessions.json to new location")
                return store
            except Exception as e:
                logger.warning(f"Failed to migrate sessions.json: {e}")
        
        # Fall back to legacy session_map.json format in new location
        if self._legacy_session_map_file.exists():
            try:
                logger.info("Migrating from legacy session_map.json to sessions.json")
                with open(self._legacy_session_map_file) as f:
                    legacy_map = json.load(f)
                
                # Convert legacy {key: id} to {key: SessionEntry}
                store = SessionStore(root={})
                now = int(datetime.now(UTC).timestamp() * 1000)
                
                for session_key, session_id in legacy_map.items():
                    entry = SessionEntry(
                        sessionId=session_id,
                        updatedAt=now,
                    )
                    store.set(session_key, entry)
                
                # Save in new format
                self._save_session_store(store)
                logger.info(f"Migrated {len(legacy_map)} sessions to new format")
                
                return store
            except Exception as e:
                logger.warning(f"Failed to migrate session map: {e}")
        
        # Fall back to legacy session_map.json in old location
        if hasattr(self, '_legacy_legacy_map_file') and self._legacy_legacy_map_file.exists():
            try:
                logger.info(f"Migrating from legacy location: {self._legacy_legacy_map_file}")
                with open(self._legacy_legacy_map_file) as f:
                    legacy_map = json.load(f)
                
                # Convert legacy {key: id} to {key: SessionEntry}
                store = SessionStore(root={})
                now = int(datetime.now(UTC).timestamp() * 1000)
                
                for session_key, session_id in legacy_map.items():
                    entry = SessionEntry(
                        sessionId=session_id,
                        updatedAt=now,
                    )
                    store.set(session_key, entry)
                
                # Save in new format and location
                self._save_session_store(store)
                logger.info(f"Migrated {len(legacy_map)} sessions from old location to new format")
                
                return store
            except Exception as e:
                logger.warning(f"Failed to migrate from old location: {e}")
        
        # Return empty store
        return SessionStore(root={})

    
    def _save_session_store(self, store: SessionStore | None = None):
        """Save session store in new format with file locking."""
        if store is None:
            store = self._session_store
        
        if not self._acquire_lock(timeout=10.0):
            logger.error("Failed to acquire lock for save")
            return
        
        try:
            with open(self._sessions_file, "w") as f:
                json.dump(store.to_dict(), f, indent=2)
            
            # Update cache metadata
            self._session_store_loaded_at = time.time()
            self._session_store_file_mtime = self._sessions_file.stat().st_mtime
            logger.debug("Saved session store")
        except Exception as e:
            logger.error(f"Failed to save session store: {e}")
        finally:
            self._release_lock()

    def generate_session_id(self) -> str:
        """Generate a new UUID v4 session ID."""
        return generate_session_id()
    
    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format (UUID v4)."""
        return looks_like_session_id(session_id)

    def get_or_create_session(
        self,
        session_id: str | None = None,
        session_key: str | None = None,
        channel: str | None = None,
        peer_kind: str | None = None,
        peer_id: str | None = None,
        dm_scope: str = "main",
    ) -> Session:
        """
        Get existing session or create new one with session key support.
        
        Args:
            session_id: Direct session ID (legacy, optional)
            session_key: Session key (agent:id:..., optional)
            channel: Channel name (telegram, discord, etc.)
            peer_kind: Peer type (dm, group, channel)
            peer_id: Peer identifier
            dm_scope: DM scope mode (main, per-peer, per-channel-peer, per-account-channel-peer)
        
        Returns:
            Session instance
        """
        # Build session key if not provided
        if session_key is None and channel and peer_kind and peer_id:
            session_key = build_agent_peer_session_key(
                self.agent_id,
                channel,
                peer_kind,
                peer_id,
                dm_scope=dm_scope
            )
        elif session_key is None and session_id is None:
            session_key = build_agent_main_session_key(self.agent_id)
        
        # Look up or create session ID using SessionStore (with caching)
        store = self._get_session_store()
        logger.info(f"get_or_create_session: session_key={session_key}, existing_keys={list(store.keys())}")
        
        entry = store.get(session_key) if session_key else None
        
        if entry:
            session_id = entry.sessionId
            logger.info(f"Found existing session: {session_key} -> {session_id}")
            # Update timestamp
            entry.updatedAt = int(datetime.now(UTC).timestamp() * 1000)
            self._save_session_store()
        else:
            # Generate new session ID if not provided or invalid
            if session_id is None or not self.validate_session_id(session_id):
                session_id = self.generate_session_id()
            
            # Create new SessionEntry
            if session_key:
                now = int(datetime.now(UTC).timestamp() * 1000)
                entry = SessionEntry(
                    sessionId=session_id,
                    updatedAt=now,
                )
                store.set(session_key, entry)
                self._session_store = store  # Update cache
                self._save_session_store()
                logger.info(f"Created NEW session: {session_key} -> {session_id}, store now has {len(store.keys())} keys")
        
        # Get or create session instance
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(
                session_id,
                self.workspace_dir,
                session_key=session_key  # Pass session_key for reference
            )
        
        return self._sessions[session_id]

    def get_or_create_session_by_key(self, session_key: str) -> Session:
        """
        Get or create session using session key (simpler wrapper).
        
        This method queries the session store for the UUID associated with the key,
        creates a new UUID if the key doesn't exist, and returns the Session object.
        
        Args:
            session_key: Session key (e.g., "agent:main:telegram:dm:8366053063")
            
        Returns:
            Session instance using UUID
        """
        return self.get_or_create_session(session_key=session_key)
    
    def get_session(self, session_id: str) -> Session:
        """
        Get or create a session (legacy method)

        Args:
            session_id: Unique session identifier

        Returns:
            Session instance
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id, self.workspace_dir)
        return self._sessions[session_id]

    def list_sessions(self) -> list[str]:
        """
        List all session IDs

        Returns:
            List of session IDs
        """
        sessions_dir = self.workspace_dir / ".sessions"
        if not sessions_dir.exists():
            return []

        session_ids = []
        for f in sessions_dir.glob("*.json"):
            if f.name != "session_map.json":  # Exclude session map file
                session_ids.append(f.stem)

        return sorted(session_ids)
    
    def get_session_key_for_id(self, session_id: str) -> str | None:
        """Get session key for given session ID."""
        for key, entry in self._session_store.items():
            if entry.sessionId == session_id:
                return key
        return None
    
    def list_sessions_by_channel(self, channel: str) -> dict[str, str]:
        """List all sessions for a specific channel."""
        sessions = {}
        for key, entry in self._session_store.items():
            parsed = parse_agent_session_key(key)
            if parsed and channel in parsed.rest:
                sessions[key] = entry.sessionId
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: Session to delete

        Returns:
            True if deleted, False if not found
        """
        # Remove from memory
        if session_id in self._sessions:
            del self._sessions[session_id]

        # Remove from session map
        keys_to_remove = [k for k, entry in self._session_store.items() if entry.sessionId == session_id]
        for key in keys_to_remove:
            self._session_store.delete(key)
        
        if keys_to_remove:
            self._save_session_store()
            logger.info(f"Removed {len(keys_to_remove)} session key(s) for {session_id}")

        # Remove from disk
        session_file = self.workspace_dir / ".sessions" / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
            return True

        return False

    def get_all_sessions(self) -> list[Session]:
        """
        Get all sessions

        Returns:
            List of Session instances
        """
        session_ids = self.list_sessions()
        return [self.get_session(sid) for sid in session_ids]

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """
        Delete sessions older than max_age_days

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        deleted = 0

        for session in self.get_all_sessions():
            try:
                updated = datetime.fromisoformat(session.updated_at.replace("Z", "+00:00"))
                if updated < cutoff:
                    if self.delete_session(session.session_id):
                        deleted += 1
            except Exception:
                pass

        return deleted
