"""
Auth profile rotation with cooldown management
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from .profile import AuthProfile, ProfileStore

logger = logging.getLogger(__name__)


class RotationManager:
    """
    Manage authentication profile rotation with cooldown

    Features:
    - Automatic failover to next available profile
    - Cooldown period after failures
    - Rate limit handling
    - Usage tracking
    """

    DEFAULT_COOLDOWN_MINUTES = 5
    DEFAULT_MAX_FAILURES = 3

    def __init__(
        self,
        store: ProfileStore,
        cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES,
        max_failures: int = DEFAULT_MAX_FAILURES,
    ):
        """
        Initialize rotation manager

        Args:
            store: Profile store
            cooldown_minutes: Minutes to cool down after failure
            max_failures: Max failures before cooldown
        """
        self.store = store
        self.cooldown_minutes = cooldown_minutes
        self.max_failures = max_failures

    def get_next_profile(
        self,
        provider: str,
        preferred_id: str | None = None,
        filter_fn: Callable[[AuthProfile], bool] | None = None,
    ) -> AuthProfile | None:
        """
        Get next available profile for provider

        Args:
            provider: Provider name
            preferred_id: Preferred profile ID (if available)
            filter_fn: Optional filter function

        Returns:
            Available profile or None
        """
        profiles = self.store.list_profiles(provider)

        if not profiles:
            logger.warning(f"No profiles found for provider: {provider}")
            return None

        # Apply filter if provided
        if filter_fn:
            profiles = [p for p in profiles if filter_fn(p)]

        # Filter out unavailable profiles
        available = [p for p in profiles if p.is_available()]

        if not available:
            logger.warning(f"All profiles for {provider} are in cooldown")
            return None

        # Try preferred profile first
        if preferred_id:
            for profile in available:
                if profile.id == preferred_id:
                    return profile

        # Sort by last used (least recently used first)
        available.sort(key=lambda p: p.last_used or datetime.min)

        return available[0]

    def mark_success(self, profile_id: str) -> None:
        """
        Mark profile as successfully used

        Args:
            profile_id: Profile ID
        """
        profile = self.store.get_profile(profile_id)
        if profile:
            profile.last_used = datetime.now(UTC)
            profile.failure_count = 0
            profile.cooldown_until = None
            self.store.add_profile(profile)
            logger.debug(f"Profile {profile_id} used successfully")

    def mark_failure(
        self, profile_id: str, reason: str = "unknown", is_rate_limit: bool = False
    ) -> None:
        """
        Mark profile as failed and apply cooldown if needed

        Args:
            profile_id: Profile ID
            reason: Failure reason
            is_rate_limit: Whether failure was due to rate limit
        """
        profile = self.store.get_profile(profile_id)
        if not profile:
            return

        profile.failure_count += 1

        # Apply cooldown if too many failures or rate limit
        if profile.failure_count >= self.max_failures or is_rate_limit:
            cooldown_minutes = self.cooldown_minutes

            # Longer cooldown for rate limits
            if is_rate_limit:
                cooldown_minutes *= 2

            profile.cooldown_until = datetime.now(UTC) + timedelta(minutes=cooldown_minutes)

            logger.warning(
                f"Profile {profile_id} in cooldown until {profile.cooldown_until} "
                f"(reason: {reason}, failures: {profile.failure_count})"
            )

        self.store.add_profile(profile)

    def reset_profile(self, profile_id: str) -> None:
        """
        Reset profile cooldown and failures

        Args:
            profile_id: Profile ID
        """
        profile = self.store.get_profile(profile_id)
        if profile:
            profile.failure_count = 0
            profile.cooldown_until = None
            self.store.add_profile(profile)
            logger.info(f"Profile {profile_id} reset")

    def get_status(self, provider: str | None = None) -> dict:
        """
        Get rotation status

        Args:
            provider: Filter by provider (optional)

        Returns:
            Status dictionary
        """
        profiles = self.store.list_profiles(provider)

        available = [p for p in profiles if p.is_available()]
        in_cooldown = [p for p in profiles if not p.is_available()]

        return {
            "total": len(profiles),
            "available": len(available),
            "in_cooldown": len(in_cooldown),
            "profiles": [
                {
                    "id": p.id,
                    "provider": p.provider,
                    "available": p.is_available(),
                    "failures": p.failure_count,
                    "cooldown_until": p.cooldown_until.isoformat() if p.cooldown_until else None,
                }
                for p in profiles
            ],
        }
