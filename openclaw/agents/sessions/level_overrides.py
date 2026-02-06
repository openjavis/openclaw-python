"""Session-level think/verbose level overrides."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import json


@dataclass
class LevelOverride:
    """Level overrides for a session."""
    
    think_level: Optional[str] = None
    verbose_level: Optional[str] = None
    reasoning_level: Optional[str] = None


class SessionLevelOverrides:
    """Manages session-level overrides."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("./data/session_levels.json")
        self.overrides: dict[str, LevelOverride] = {}
        self._load()
    
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            for session_key, override_data in data.items():
                self.overrides[session_key] = LevelOverride(**override_data)
        except Exception:
            pass
    
    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            session_key: {
                "think_level": override.think_level,
                "verbose_level": override.verbose_level,
                "reasoning_level": override.reasoning_level
            }
            for session_key, override in self.overrides.items()
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def set_override(
        self,
        session_key: str,
        think_level: Optional[str] = None,
        verbose_level: Optional[str] = None,
        reasoning_level: Optional[str] = None
    ) -> None:
        self.overrides[session_key] = LevelOverride(
            think_level=think_level,
            verbose_level=verbose_level,
            reasoning_level=reasoning_level
        )
        self._save()
    
    def get_override(self, session_key: str) -> Optional[LevelOverride]:
        return self.overrides.get(session_key)
    
    def clear_override(self, session_key: str) -> None:
        if session_key in self.overrides:
            del self.overrides[session_key]
            self._save()
