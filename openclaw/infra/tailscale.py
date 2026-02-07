"""
Tailscale authentication integration

Provides Tailscale whois lookup and authentication.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TailscaleWhoisIdentity:
    """Tailscale user identity from whois."""

    login: str
    name: str
    profile_pic: str | None = None
    user_id: str | None = None
    node_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict."""
        return {
            "login": self.login,
            "name": self.name,
            "profile_pic": self.profile_pic,
            "user_id": self.user_id,
            "node_name": self.node_name,
        }


class TailscaleAuthProvider:
    """
    Tailscale authentication provider.

    Provides Tailscale whois lookup and user verification.
    """

    def __init__(self, tailscale_bin: str = "tailscale"):
        """
        Initialize Tailscale auth provider.

        Args:
            tailscale_bin: Path to tailscale binary
        """
        self.tailscale_bin = tailscale_bin

        # Check if tailscale is available
        self._check_available()

    def _check_available(self) -> bool:
        """Check if Tailscale CLI is available."""
        try:
            result = subprocess.run(
                [self.tailscale_bin, "version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info(f"Tailscale available: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Tailscale not available: {e}")

        return False

    def whois_lookup(self, ip: str) -> TailscaleWhoisIdentity | None:
        """
        Perform Tailscale whois lookup for an IP address.

        Args:
            ip: IP address to lookup

        Returns:
            TailscaleWhoisIdentity if found, None otherwise
        """
        try:
            result = subprocess.run(
                [self.tailscale_bin, "whois", "--json", ip],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                logger.warning(f"Tailscale whois failed for {ip}: {result.stderr}")
                return None

            data = json.loads(result.stdout)

            # Extract user info
            user_profile = data.get("UserProfile", {})
            node = data.get("Node", {})

            if not user_profile:
                logger.warning(f"No user profile in whois result for {ip}")
                return None

            identity = TailscaleWhoisIdentity(
                login=user_profile.get("LoginName", ""),
                name=user_profile.get("DisplayName", ""),
                profile_pic=user_profile.get("ProfilePicURL"),
                user_id=user_profile.get("ID"),
                node_name=node.get("Name"),
            )

            logger.info(f"Tailscale whois: {ip} -> {identity.login}")
            return identity

        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            logger.error(f"Tailscale whois error for {ip}: {e}")
            return None

    def verify_user(
        self,
        ip: str,
        expected_login: str,
    ) -> tuple[bool, TailscaleWhoisIdentity | None]:
        """
        Verify that an IP belongs to a specific Tailscale user.

        Args:
            ip: Client IP address
            expected_login: Expected Tailscale login (e.g., "user@example.com")

        Returns:
            (is_verified, identity)
        """
        identity = self.whois_lookup(ip)

        if not identity:
            return False, None

        # Normalize logins for comparison
        actual_login = identity.login.lower().strip()
        expected_login = expected_login.lower().strip()

        if actual_login == expected_login:
            logger.info(f"Tailscale user verified: {expected_login}")
            return True, identity

        logger.warning(f"Tailscale user mismatch: expected {expected_login}, got {actual_login}")
        return False, identity


def read_tailscale_whois_identity(ip: str) -> TailscaleWhoisIdentity | None:
    """
    Read Tailscale whois identity for an IP (matches TS function signature).

    Args:
        ip: IP address

    Returns:
        TailscaleWhoisIdentity if found, None otherwise
    """
    provider = TailscaleAuthProvider()
    return provider.whois_lookup(ip)
