"""Session-level model overrides.

Allows different sessions to use different models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import json


@dataclass
class ModelOverride:
    """Model override for a session."""
    
    provider: Optional[str] = None
    model: Optional[str] = None
    think_level: Optional[str] = None


class SessionModelOverrides:
    """Manages session-level model overrides."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize overrides manager.
        
        Args:
            storage_path: Path to store overrides (JSON file)
        """
        self.storage_path = storage_path or Path("./data/session_overrides.json")
        self.overrides: dict[str, ModelOverride] = {}
        self._load()
    
    def _load(self) -> None:
        """Load overrides from storage."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            for session_key, override_data in data.items():
                self.overrides[session_key] = ModelOverride(**override_data)
        except Exception:
            pass
    
    def _save(self) -> None:
        """Save overrides to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            session_key: {
                "provider": override.provider,
                "model": override.model,
                "think_level": override.think_level
            }
            for session_key, override in self.overrides.items()
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def set_override(
        self,
        session_key: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        think_level: Optional[str] = None
    ) -> None:
        """Set model override for session.
        
        Args:
            session_key: Session key
            provider: Override provider
            model: Override model
            think_level: Override think level
        """
        self.overrides[session_key] = ModelOverride(
            provider=provider,
            model=model,
            think_level=think_level
        )
        self._save()
    
    def get_override(self, session_key: str) -> Optional[ModelOverride]:
        """Get model override for session.
        
        Args:
            session_key: Session key
        
        Returns:
            ModelOverride if exists, None otherwise
        """
        return self.overrides.get(session_key)
    
    def clear_override(self, session_key: str) -> None:
        """Clear model override for session.
        
        Args:
            session_key: Session key
        """
        if session_key in self.overrides:
            del self.overrides[session_key]
            self._save()
    
    def apply_override(
        self,
        session_key: str,
        default_provider: str,
        default_model: str,
        default_think_level: Optional[str] = None
    ) -> dict[str, any]:
        """Apply override to defaults.
        
        Args:
            session_key: Session key
            default_provider: Default provider
            default_model: Default model
            default_think_level: Default think level
        
        Returns:
            Dictionary with effective values
        """
        override = self.get_override(session_key)
        
        if not override:
            return {
                "provider": default_provider,
                "model": default_model,
                "think_level": default_think_level
            }
        
        return {
            "provider": override.provider or default_provider,
            "model": override.model or default_model,
            "think_level": override.think_level or default_think_level
        }
