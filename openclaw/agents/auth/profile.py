"""
Auth profile data structures
"""

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class AuthProfile:
    """
    Authentication profile for API access

    Attributes:
        id: Unique profile identifier
        provider: Provider name (anthropic, openai, etc.)
        api_key: API key (can be env var name)
        last_used: Last time this profile was used
        failure_count: Number of consecutive failures
        cooldown_until: When this profile becomes available again
        metadata: Additional profile metadata
    """

    id: str
    provider: str
    api_key: str
    last_used: datetime | None = None
    failure_count: int = 0
    cooldown_until: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if profile is available (not in cooldown)"""
        if self.cooldown_until is None:
            return True
        return datetime.now(UTC) >= self.cooldown_until

    def get_api_key(self) -> str:
        """
        Get actual API key value

        If api_key starts with '$', treat as env var name
        """
        if self.api_key.startswith("$"):
            env_var = self.api_key[1:]
            return os.getenv(env_var, "")
        return self.api_key

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "provider": self.provider,
            "api_key": self.api_key,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "failure_count": self.failure_count,
            "cooldown_until": self.cooldown_until.isoformat() if self.cooldown_until else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthProfile":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            provider=data["provider"],
            api_key=data["api_key"],
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            failure_count=data.get("failure_count", 0),
            cooldown_until=(
                datetime.fromisoformat(data["cooldown_until"])
                if data.get("cooldown_until")
                else None
            ),
            metadata=data.get("metadata", {}),
        )


class ProfileStore:
    """
    Store and manage authentication profiles
    """

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize profile store

        Args:
            config_dir: Directory to store profile config
        """
        self.config_dir = config_dir or Path.home() / ".openclaw"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "auth_profiles.json"

        self.profiles: dict[str, AuthProfile] = {}
        self._load()

    def add_profile(self, profile: AuthProfile) -> None:
        """Add or update a profile"""
        self.profiles[profile.id] = profile
        self._save()

    def get_profile(self, profile_id: str) -> AuthProfile | None:
        """Get profile by ID"""
        return self.profiles.get(profile_id)

    def list_profiles(self, provider: str | None = None) -> list[AuthProfile]:
        """
        List profiles, optionally filtered by provider

        Args:
            provider: Filter by provider (optional)

        Returns:
            List of profiles
        """
        profiles = list(self.profiles.values())
        if provider:
            profiles = [p for p in profiles if p.provider == provider]
        return profiles

    def remove_profile(self, profile_id: str) -> bool:
        """Remove a profile"""
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            self._save()
            return True
        return False

    def _load(self) -> None:
        """Load profiles from disk"""
        if not self.config_file.exists():
            return

        try:
            with open(self.config_file) as f:
                data = json.load(f)
                self.profiles = {pid: AuthProfile.from_dict(pdata) for pid, pdata in data.items()}
        except Exception as e:
            print(f"Warning: Failed to load profiles: {e}")

    def _save(self) -> None:
        """Save profiles to disk"""
        try:
            data = {pid: p.to_dict() for pid, p in self.profiles.items()}
            with open(self.config_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save profiles: {e}")
