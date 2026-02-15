"""
System Presence - tracks connected instances and nodes

Aligned with openclaw/src/infra/system-presence.ts
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

# Global presence registry
_presence_registry: dict[str, SystemPresence] = {}


@dataclass
class SystemPresence:
    """System presence beacon"""
    id: str
    type: Literal["gateway", "client", "node"]
    version: str
    since: str  # ISO timestamp
    last_seen: str  # ISO timestamp
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dict for API response"""
        return {
            "id": self.id,
            "type": self.type,
            "version": self.version,
            "since": self.since,
            "lastSeen": self.last_seen,
            "metadata": self.metadata,
        }


def register_presence(presence: SystemPresence) -> None:
    """Register or update system presence"""
    _presence_registry[presence.id] = presence


def update_presence(presence_id: str) -> None:
    """Update last_seen timestamp for a presence"""
    if presence_id in _presence_registry:
        _presence_registry[presence_id].last_seen = datetime.now(UTC).isoformat()


def unregister_presence(presence_id: str) -> bool:
    """Unregister system presence"""
    if presence_id in _presence_registry:
        del _presence_registry[presence_id]
        return True
    return False


def list_system_presence() -> list[dict]:
    """List all system presences"""
    return [p.to_dict() for p in _presence_registry.values()]


def get_presence(presence_id: str) -> SystemPresence | None:
    """Get specific presence by ID"""
    return _presence_registry.get(presence_id)
