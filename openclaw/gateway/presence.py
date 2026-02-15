"""
System presence management with deduplication.

This module manages presence entries showing which devices/systems are online.
Key feature: Deduplicates by device ID - same device connecting as both
operator and node shows as single presence entry.

Reference: openclaw/docs/concepts/presence.md
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PresenceEntry:
    """System presence entry"""
    
    host: str
    ip: str
    version: str
    platform: str | None = None
    deviceFamily: str | None = None
    modelIdentifier: str | None = None
    mode: str = "active"
    lastInputSeconds: int | None = None
    ts: float = field(default_factory=time.time)
    reason: str | None = None
    tags: list[str] = field(default_factory=list)
    instanceId: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "host": self.host,
            "ip": self.ip,
            "version": self.version,
            "platform": self.platform,
            "deviceFamily": self.deviceFamily,
            "modelIdentifier": self.modelIdentifier,
            "mode": self.mode,
            "lastInputSeconds": self.lastInputSeconds,
            "ts": int(self.ts * 1000),  # Milliseconds
            "reason": self.reason,
            "tags": self.tags,
            "instanceId": self.instanceId,
        }


class PresenceManager:
    """
    Manage system presence with device deduplication.
    
    Key feature: Deduplicates by device ID. If the same device connects
    as both operator and node, only one presence entry is shown.
    
    Usage:
        manager = PresenceManager()
        
        # Update presence
        state_version = manager.update("device_123", PresenceEntry(...))
        
        # Get snapshot
        snapshot = manager.get_snapshot()
        
        # Remove on disconnect
        manager.remove("device_123")
        
        # Include in hello-ok
        hello_ok_payload = {
            "presence": manager.get_snapshot()
        }
    """
    
    def __init__(self):
        """Initialize presence manager"""
        self._entries: dict[str, PresenceEntry] = {}  # deviceId -> entry
        self._state_version = 0
    
    def update(self, device_id: str, entry: PresenceEntry) -> int:
        """
        Update presence entry and increment state version.
        
        Args:
            device_id: Device ID
            entry: Presence entry
            
        Returns:
            New state version
        """
        self._entries[device_id] = entry
        self._state_version += 1
        return self._state_version
    
    def remove(self, device_id: str) -> int:
        """
        Remove presence entry.
        
        Args:
            device_id: Device ID
            
        Returns:
            New state version
        """
        if device_id in self._entries:
            del self._entries[device_id]
            self._state_version += 1
        return self._state_version
    
    def get(self, device_id: str) -> PresenceEntry | None:
        """
        Get presence entry by device ID.
        
        Args:
            device_id: Device ID
            
        Returns:
            Presence entry if found, None otherwise
        """
        return self._entries.get(device_id)
    
    def get_snapshot(self) -> dict[str, Any]:
        """
        Get full presence snapshot.
        
        Returns:
            Snapshot with entries and state version
        """
        return {
            "entries": [entry.to_dict() for entry in self._entries.values()],
            "stateVersion": self._state_version
        }
    
    def get_delta(self, since_version: int) -> dict[str, Any] | None:
        """
        Get presence delta since version.
        
        For now, returns full snapshot. Future optimization could track
        deltas for efficient updates.
        
        Args:
            since_version: Last known state version
            
        Returns:
            Delta or full snapshot
        """
        # TODO: Track deltas for efficient updates
        # For now, return full snapshot
        return self.get_snapshot()
    
    def list_entries(self) -> list[PresenceEntry]:
        """
        List all presence entries.
        
        Returns:
            List of presence entries
        """
        return list(self._entries.values())
    
    def count(self) -> int:
        """Get number of presence entries"""
        return len(self._entries)
    
    def clear(self) -> None:
        """Clear all presence entries"""
        self._entries.clear()
        self._state_version += 1


__all__ = [
    "PresenceEntry",
    "PresenceManager",
]
