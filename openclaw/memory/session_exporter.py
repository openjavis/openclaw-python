"""Session exporter for memory sync

Exports agent sessions to memory index.
Tracks session deltas and triggers re-indexing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionDelta:
    """Session change delta"""
    
    session_id: str
    bytes_added: int
    messages_added: int
    last_export_time: float


class SessionExporter:
    """
    Session exporter for memory
    
    Tracks session changes and exports to memory index when thresholds reached.
    """
    
    def __init__(
        self,
        byte_threshold: int = 10000,  # 10KB
        message_threshold: int = 10,
        time_threshold: float = 300.0,  # 5 minutes
    ):
        """
        Initialize session exporter
        
        Args:
            byte_threshold: Bytes threshold for export
            message_threshold: Message count threshold
            time_threshold: Time threshold (seconds)
        """
        self.byte_threshold = byte_threshold
        self.message_threshold = message_threshold
        self.time_threshold = time_threshold
        
        # Track deltas
        self.deltas: dict[str, SessionDelta] = {}
    
    def track_message(
        self,
        session_id: str,
        message: dict[str, Any],
    ) -> bool:
        """
        Track new message
        
        Args:
            session_id: Session ID
            message: Message data
            
        Returns:
            True if export threshold reached
        """
        import time
        
        # Get or create delta
        if session_id not in self.deltas:
            self.deltas[session_id] = SessionDelta(
                session_id=session_id,
                bytes_added=0,
                messages_added=0,
                last_export_time=time.time(),
            )
        
        delta = self.deltas[session_id]
        
        # Calculate message size
        message_bytes = len(str(message).encode())
        
        # Update delta
        delta.bytes_added += message_bytes
        delta.messages_added += 1
        
        # Check thresholds
        return self.should_export(session_id)
    
    def should_export(self, session_id: str) -> bool:
        """
        Check if session should be exported
        
        Args:
            session_id: Session ID
            
        Returns:
            True if should export
        """
        import time
        
        if session_id not in self.deltas:
            return False
        
        delta = self.deltas[session_id]
        
        # Check byte threshold
        if delta.bytes_added >= self.byte_threshold:
            logger.debug(f"Session {session_id} reached byte threshold")
            return True
        
        # Check message threshold
        if delta.messages_added >= self.message_threshold:
            logger.debug(f"Session {session_id} reached message threshold")
            return True
        
        # Check time threshold
        age = time.time() - delta.last_export_time
        if age >= self.time_threshold:
            logger.debug(f"Session {session_id} reached time threshold")
            return True
        
        return False
    
    async def export_session(
        self,
        session_id: str,
        session_path: Path,
        memory_manager: Any,
    ) -> None:
        """
        Export session to memory
        
        Args:
            session_id: Session ID
            session_path: Path to session file
            memory_manager: Memory manager instance
        """
        import time
        
        logger.info(f"Exporting session {session_id} to memory")
        
        try:
            # Add session file to memory
            from .types import MemorySource
            
            chunks_added = await memory_manager.add_file(
                file_path=session_path,
                source=MemorySource.SESSIONS,
            )
            
            logger.info(
                f"Exported session {session_id}: {chunks_added} chunks added"
            )
            
            # Reset delta
            if session_id in self.deltas:
                delta = self.deltas[session_id]
                delta.bytes_added = 0
                delta.messages_added = 0
                delta.last_export_time = time.time()
            
        except Exception as e:
            logger.error(f"Error exporting session {session_id}: {e}", exc_info=True)
    
    def get_stats(self) -> dict[str, Any]:
        """Get exporter statistics"""
        total_bytes = sum(d.bytes_added for d in self.deltas.values())
        total_messages = sum(d.messages_added for d in self.deltas.values())
        
        return {
            "tracked_sessions": len(self.deltas),
            "total_bytes": total_bytes,
            "total_messages": total_messages,
        }
