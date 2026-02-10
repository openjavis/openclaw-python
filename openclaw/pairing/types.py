"""Pairing type definitions"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass
class PairingRequest:
    """Pending pairing request"""
    
    id: str  # Sender ID
    code: str  # 8-character pairing code
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    meta: dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "code": self.code,
            "created_at": self.created_at,
            "last_seen_at": self.last_seen_at,
            "meta": self.meta,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PairingRequest:
        """Create from dictionary"""
        return cls(
            id=data["id"],
            code=data["code"],
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            last_seen_at=data.get("last_seen_at", datetime.now(timezone.utc).isoformat()),
            meta=data.get("meta", {}),
        )


@dataclass
class ChannelPairingAdapter:
    """Channel-specific pairing adapter"""
    
    id_label: str  # e.g., "userId", "phone number"
    normalize_allow_entry: Callable[[str], str] | None = None
    notify_approval: Callable[[str, str, dict[str, Any]], Any] | None = None
    
    def normalize_entry(self, entry: str) -> str:
        """Normalize allowlist entry"""
        if self.normalize_allow_entry:
            return self.normalize_allow_entry(entry)
        return entry
    
    async def send_approval_notification(
        self,
        channel_id: str,
        user_id: str,
        meta: dict[str, Any]
    ) -> None:
        """Send approval notification"""
        if self.notify_approval:
            await self.notify_approval(channel_id, user_id, meta)
