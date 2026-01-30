"""
Tests for auth profile rotation
"""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from openclaw.agents.auth import AuthProfile, ProfileStore, RotationManager


class TestAuthProfile:
    """Test AuthProfile class"""

    def test_profile_creation(self):
        """Test creating a profile"""
        profile = AuthProfile(id="test-profile", provider="anthropic", api_key="sk-test-key")

        assert profile.id == "test-profile"
        assert profile.provider == "anthropic"
        assert profile.is_available()

    def test_profile_cooldown(self):
        """Test profile cooldown"""
        profile = AuthProfile(
            id="test",
            provider="anthropic",
            api_key="key",
            cooldown_until=datetime.now(UTC) + timedelta(minutes=5),
        )

        assert not profile.is_available()

    def test_profile_env_var(self):
        """Test API key from env var"""
        import os

        os.environ["TEST_API_KEY"] = "secret-key"

        profile = AuthProfile(id="test", provider="test", api_key="$TEST_API_KEY")

        assert profile.get_api_key() == "secret-key"

    def test_profile_to_dict(self):
        """Test serialization"""
        profile = AuthProfile(id="test", provider="anthropic", api_key="key")

        data = profile.to_dict()

        assert data["id"] == "test"
        assert data["provider"] == "anthropic"
        assert data["api_key"] == "key"


class TestProfileStore:
    """Test ProfileStore class"""

    def test_store_initialization(self, tmp_path):
        """Test store initialization"""
        store = ProfileStore(tmp_path)
        assert store.config_dir == tmp_path
        assert len(store.profiles) == 0

    def test_add_profile(self, tmp_path):
        """Test adding a profile"""
        store = ProfileStore(tmp_path)
        profile = AuthProfile(id="test", provider="anthropic", api_key="key")

        store.add_profile(profile)

        assert "test" in store.profiles
        assert store.get_profile("test") == profile

    def test_list_profiles(self, tmp_path):
        """Test listing profiles"""
        store = ProfileStore(tmp_path)
        store.add_profile(AuthProfile(id="p1", provider="anthropic", api_key="k1"))
        store.add_profile(AuthProfile(id="p2", provider="openai", api_key="k2"))
        store.add_profile(AuthProfile(id="p3", provider="anthropic", api_key="k3"))

        all_profiles = store.list_profiles()
        assert len(all_profiles) == 3

        anthropic_profiles = store.list_profiles("anthropic")
        assert len(anthropic_profiles) == 2

    def test_remove_profile(self, tmp_path):
        """Test removing a profile"""
        store = ProfileStore(tmp_path)
        store.add_profile(AuthProfile(id="test", provider="anthropic", api_key="key"))

        removed = store.remove_profile("test")
        assert removed
        assert store.get_profile("test") is None

    def test_persistence(self, tmp_path):
        """Test profile persistence"""
        # Create and save
        store1 = ProfileStore(tmp_path)
        store1.add_profile(AuthProfile(id="test", provider="anthropic", api_key="key"))

        # Load in new store
        store2 = ProfileStore(tmp_path)
        profile = store2.get_profile("test")

        assert profile is not None
        assert profile.id == "test"


class TestRotationManager:
    """Test RotationManager class"""

    def test_get_next_profile(self, tmp_path):
        """Test getting next available profile"""
        store = ProfileStore(tmp_path)
        store.add_profile(AuthProfile(id="p1", provider="anthropic", api_key="k1"))
        store.add_profile(AuthProfile(id="p2", provider="anthropic", api_key="k2"))

        manager = RotationManager(store)
        profile = manager.get_next_profile("anthropic")

        assert profile is not None
        assert profile.provider == "anthropic"

    def test_preferred_profile(self, tmp_path):
        """Test preferred profile selection"""
        store = ProfileStore(tmp_path)
        store.add_profile(AuthProfile(id="p1", provider="anthropic", api_key="k1"))
        store.add_profile(AuthProfile(id="p2", provider="anthropic", api_key="k2"))

        manager = RotationManager(store)
        profile = manager.get_next_profile("anthropic", preferred_id="p2")

        assert profile.id == "p2"

    def test_skip_cooldown_profiles(self, tmp_path):
        """Test skipping profiles in cooldown"""
        store = ProfileStore(tmp_path)
        p1 = AuthProfile(
            id="p1",
            provider="anthropic",
            api_key="k1",
            cooldown_until=datetime.now(UTC) + timedelta(hours=1),
        )
        p2 = AuthProfile(id="p2", provider="anthropic", api_key="k2")
        store.add_profile(p1)
        store.add_profile(p2)

        manager = RotationManager(store)
        profile = manager.get_next_profile("anthropic")

        assert profile.id == "p2"  # Should skip p1

    def test_mark_success(self, tmp_path):
        """Test marking profile as successful"""
        store = ProfileStore(tmp_path)
        profile = AuthProfile(id="test", provider="anthropic", api_key="key", failure_count=3)
        store.add_profile(profile)

        manager = RotationManager(store)
        manager.mark_success("test")

        updated = store.get_profile("test")
        assert updated.failure_count == 0
        assert updated.last_used is not None

    def test_mark_failure_cooldown(self, tmp_path):
        """Test marking profile as failed with cooldown"""
        store = ProfileStore(tmp_path)
        profile = AuthProfile(id="test", provider="anthropic", api_key="key")
        store.add_profile(profile)

        manager = RotationManager(store, cooldown_minutes=10, max_failures=2)

        # First failure - no cooldown yet
        manager.mark_failure("test")
        assert store.get_profile("test").failure_count == 1
        assert store.get_profile("test").cooldown_until is None

        # Second failure - triggers cooldown
        manager.mark_failure("test")
        updated = store.get_profile("test")
        assert updated.failure_count == 2
        assert updated.cooldown_until is not None

    def test_mark_failure_rate_limit(self, tmp_path):
        """Test immediate cooldown for rate limits"""
        store = ProfileStore(tmp_path)
        store.add_profile(AuthProfile(id="test", provider="anthropic", api_key="key"))

        manager = RotationManager(store, cooldown_minutes=5)
        manager.mark_failure("test", reason="rate_limit", is_rate_limit=True)

        profile = store.get_profile("test")
        assert profile.cooldown_until is not None

    def test_reset_profile(self, tmp_path):
        """Test resetting profile"""
        store = ProfileStore(tmp_path)
        profile = AuthProfile(
            id="test",
            provider="anthropic",
            api_key="key",
            failure_count=5,
            cooldown_until=datetime.now(UTC) + timedelta(hours=1),
        )
        store.add_profile(profile)

        manager = RotationManager(store)
        manager.reset_profile("test")

        updated = store.get_profile("test")
        assert updated.failure_count == 0
        assert updated.cooldown_until is None
