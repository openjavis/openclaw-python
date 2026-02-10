"""Persistent storage for pairing data with file locking"""
from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # Windows doesn't have fcntl
    HAS_FCNTL = False

logger = logging.getLogger(__name__)


class PairingStorage:
    """
    Persistent storage for pairing data
    
    Features:
    - File permissions: 0o600 (owner read/write only)
    - Directory permissions: 0o700 (owner access only)
    - Atomic writes: temp file + rename
    - File locking (on Unix systems)
    """
    
    def __init__(self, state_dir: Path):
        """
        Initialize storage
        
        Args:
            state_dir: State directory (e.g., ~/.openclaw/oauth/)
        """
        self.state_dir = state_dir
        
        # Ensure directory exists with secure permissions
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    
    def get_pairing_file(self, channel: str) -> Path:
        """Get pairing requests file path"""
        return self.state_dir / f"{self._safe_channel_key(channel)}-pairing.json"
    
    def get_allowfrom_file(self, channel: str) -> Path:
        """Get allowFrom file path"""
        return self.state_dir / f"{self._safe_channel_key(channel)}-allowFrom.json"
    
    def _safe_channel_key(self, channel: str) -> str:
        """
        Sanitize channel key to prevent path traversal
        
        Args:
            channel: Channel identifier
            
        Returns:
            Sanitized channel key
        """
        # Remove any path separators and dangerous characters
        safe = "".join(c for c in channel if c.isalnum() or c in "-_")
        
        if not safe:
            raise ValueError(f"Invalid channel key: {channel}")
        
        return safe
    
    def load_pairing_requests(self, channel: str) -> dict[str, Any]:
        """
        Load pairing requests for channel
        
        Args:
            channel: Channel identifier
            
        Returns:
            Pairing data dictionary
        """
        file_path = self.get_pairing_file(channel)
        
        if not file_path.exists():
            return {"version": 1, "requests": []}
        
        try:
            with self._lock_file(file_path, "r") as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing pairing file: {e}")
            return {"version": 1, "requests": []}
        except Exception as e:
            logger.error(f"Error loading pairing file: {e}", exc_info=True)
            return {"version": 1, "requests": []}
    
    def save_pairing_requests(self, channel: str, data: dict[str, Any]) -> None:
        """
        Save pairing requests for channel
        
        Args:
            channel: Channel identifier
            data: Pairing data to save
        """
        file_path = self.get_pairing_file(channel)
        
        try:
            # Write to temp file first
            temp_path = file_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
            
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            
            # Set secure permissions
            os.chmod(temp_path, 0o600)
            
            # Atomic rename
            temp_path.replace(file_path)
            
            logger.debug(f"Saved pairing requests for {channel}")
            
        except Exception as e:
            logger.error(f"Error saving pairing file: {e}", exc_info=True)
            # Clean up temp file
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            raise
    
    def load_allowfrom(self, channel: str) -> list[str]:
        """
        Load allowFrom list for channel
        
        Args:
            channel: Channel identifier
            
        Returns:
            List of allowed sender IDs
        """
        file_path = self.get_allowfrom_file(channel)
        
        if not file_path.exists():
            return []
        
        try:
            with self._lock_file(file_path, "r") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("entries", [])
            
            return []
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing allowFrom file: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading allowFrom file: {e}", exc_info=True)
            return []
    
    def save_allowfrom(self, channel: str, entries: list[str]) -> None:
        """
        Save allowFrom list for channel
        
        Args:
            channel: Channel identifier
            entries: List of allowed sender IDs
        """
        file_path = self.get_allowfrom_file(channel)
        
        try:
            # Write to temp file first
            temp_path = file_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
            
            data = {
                "version": 1,
                "entries": entries
            }
            
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            
            # Set secure permissions
            os.chmod(temp_path, 0o600)
            
            # Atomic rename
            temp_path.replace(file_path)
            
            logger.debug(f"Saved allowFrom for {channel}")
            
        except Exception as e:
            logger.error(f"Error saving allowFrom file: {e}", exc_info=True)
            # Clean up temp file
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            raise
    
    def _lock_file(self, file_path: Path, mode: str):
        """
        Open file with lock (context manager)
        
        Args:
            file_path: File to lock
            mode: File open mode
            
        Returns:
            File handle
        """
        class FileLock:
            def __init__(self, path: Path, mode: str):
                self.path = path
                self.mode = mode
                self.file = None
            
            def __enter__(self):
                self.file = open(self.path, self.mode)
                
                # Lock file (Unix only)
                if HAS_FCNTL:
                    try:
                        if "r" in self.mode:
                            fcntl.flock(self.file.fileno(), fcntl.LOCK_SH)
                        else:
                            fcntl.flock(self.file.fileno(), fcntl.LOCK_EX)
                    except Exception as e:
                        logger.warning(f"Failed to lock file: {e}")
                
                return self.file
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.file:
                    # Unlock file (Unix only)
                    if HAS_FCNTL:
                        try:
                            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
                        except Exception as e:
                            logger.warning(f"Failed to unlock file: {e}")
                    
                    self.file.close()
        
        return FileLock(file_path, mode)
