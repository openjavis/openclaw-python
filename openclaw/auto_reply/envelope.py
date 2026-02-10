"""Message envelope wrapper"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .types import InboundMessage


@dataclass
class InboundEnvelope:
    """
    Envelope wrapper for inbound messages
    
    Provides:
    - Message deduplication
    - Metadata tracking
    - Processing state
    """
    
    # Core message
    message: InboundMessage
    
    # Deduplication
    message_hash: str = ""
    
    # Processing state
    processed: bool = False
    processing_started_at: float | None = None
    processing_completed_at: float | None = None
    
    # Metadata
    received_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate message hash"""
        if not self.message_hash:
            self.message_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """
        Compute unique hash for message
        
        Uses: channel_id + message_id + sender_id + text
        """
        components = [
            self.message.channel_id,
            self.message.message_id,
            self.message.sender_id,
            self.message.text or "",
        ]
        
        hash_input = "|".join(components)
        
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def mark_processing_started(self, timestamp: float) -> None:
        """Mark processing as started"""
        self.processing_started_at = timestamp
    
    def mark_processing_completed(self, timestamp: float) -> None:
        """Mark processing as completed"""
        self.processed = True
        self.processing_completed_at = timestamp
