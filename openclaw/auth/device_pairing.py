"""
Device pairing system

Matches TypeScript src/infra/device-pairing.ts

Provides secure device registration and token-based authentication.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DeviceAuthToken:
    """Device authentication token (matches TS DeviceAuthToken)."""

    token: str
    role: str
    scopes: list[str]
    created_at_ms: int
    rotated_at_ms: int | None = None
    revoked_at_ms: int | None = None
    last_used_at_ms: int | None = None

    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at_ms is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class DevicePairingRequest:
    """Pending device pairing request (matches TS DevicePairingPendingRequest)."""

    request_id: str
    device_id: str
    public_key: str
    display_name: str | None = None
    platform: str | None = None
    client_id: str | None = None
    client_mode: str | None = None
    role: str | None = None
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    remote_ip: str | None = None
    silent: bool = False
    is_repair: bool = False
    ts: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


@dataclass
class PairedDevice:
    """Paired device (matches TS PairedDevice)."""

    device_id: str
    public_key: str
    display_name: str | None = None
    platform: str | None = None
    client_id: str | None = None
    client_mode: str | None = None
    role: str | None = None
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    remote_ip: str | None = None
    tokens: dict[str, DeviceAuthToken] = field(default_factory=dict)
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    approved_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        data = asdict(self)
        # Convert DeviceAuthToken objects to dicts
        if self.tokens:
            data["tokens"] = {k: v.to_dict() for k, v in self.tokens.items()}
        return data


class DevicePairingManager:
    """
    Device pairing manager (matches TS device-pairing.ts).

    Handles:
    - Device registration requests
    - Approval/rejection workflow
    - Token generation and validation
    - Token rotation and revocation
    """

    PENDING_TTL_MS = 5 * 60 * 1000  # 5 minutes

    def __init__(self, state_dir: Path | None = None):
        """
        Initialize device pairing manager.

        Args:
            state_dir: Directory for state files (default: ~/.openclaw/devices/)
        """
        if state_dir is None:
            state_dir = Path.home() / ".openclaw" / "devices"

        self.state_dir = Path(state_dir)
        self.pending_path = self.state_dir / "pending.json"
        self.paired_path = self.state_dir / "paired.json"

        self.pending_by_id: dict[str, DevicePairingRequest] = {}
        self.paired_by_device_id: dict[str, PairedDevice] = {}

        # Load state
        self._load_state()

    def _load_state(self):
        """Load state from disk."""
        if self.pending_path.exists():
            try:
                with open(self.pending_path) as f:
                    data = json.load(f)
                    for req_id, req_data in data.items():
                        self.pending_by_id[req_id] = DevicePairingRequest(**req_data)
            except Exception:
                pass

        if self.paired_path.exists():
            try:
                with open(self.paired_path) as f:
                    data = json.load(f)
                    for device_id, device_data in data.items():
                        # Reconstruct tokens
                        tokens = {}
                        if "tokens" in device_data:
                            for role, token_data in device_data["tokens"].items():
                                tokens[role] = DeviceAuthToken(**token_data)
                            device_data["tokens"] = tokens

                        self.paired_by_device_id[device_id] = PairedDevice(**device_data)
            except Exception:
                pass

    def _save_state(self):
        """Save state to disk (atomic write)."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Save pending
        pending_data = {k: v.to_dict() for k, v in self.pending_by_id.items()}
        tmp_pending = self.pending_path.with_suffix(".tmp")
        with open(tmp_pending, "w") as f:
            json.dump(pending_data, f, indent=2)
        tmp_pending.replace(self.pending_path)

        # Save paired
        paired_data = {k: v.to_dict() for k, v in self.paired_by_device_id.items()}
        tmp_paired = self.paired_path.with_suffix(".tmp")
        with open(tmp_paired, "w") as f:
            json.dump(paired_data, f, indent=2)
        tmp_paired.replace(self.paired_path)

    def create_pairing_request(
        self,
        device_id: str,
        public_key: str,
        display_name: str | None = None,
        platform: str | None = None,
        role: str = "gateway",
        scopes: list[str] | None = None,
        remote_ip: str | None = None,
    ) -> str:
        """
        Create a new pairing request.

        Args:
            device_id: Unique device identifier
            public_key: Device public key
            display_name: Human-readable name
            platform: Platform (ios/android/web/etc.)
            role: Requested role
            scopes: Requested scopes
            remote_ip: Client IP address

        Returns:
            Request ID
        """
        request_id = secrets.token_urlsafe(16)

        request = DevicePairingRequest(
            request_id=request_id,
            device_id=device_id,
            public_key=public_key,
            display_name=display_name,
            platform=platform,
            role=role,
            scopes=scopes or ["read", "write"],
            remote_ip=remote_ip,
        )

        self.pending_by_id[request_id] = request
        self._save_state()

        return request_id

    def approve_request(self, request_id: str) -> PairedDevice | None:
        """
        Approve a pairing request.

        Args:
            request_id: Request ID

        Returns:
            PairedDevice if approved, None if not found
        """
        request = self.pending_by_id.pop(request_id, None)
        if not request:
            return None

        # Create paired device
        device = PairedDevice(
            device_id=request.device_id,
            public_key=request.public_key,
            display_name=request.display_name,
            platform=request.platform,
            role=request.role,
            scopes=request.scopes,
            remote_ip=request.remote_ip,
        )

        # Generate initial token
        token = self._generate_token()
        device.tokens[request.role or "gateway"] = DeviceAuthToken(
            token=token,
            role=request.role or "gateway",
            scopes=request.scopes,
            created_at_ms=int(time.time() * 1000),
        )

        self.paired_by_device_id[device.device_id] = device
        self._save_state()

        return device

    def reject_request(self, request_id: str) -> bool:
        """
        Reject a pairing request.

        Args:
            request_id: Request ID

        Returns:
            True if rejected, False if not found
        """
        if request_id in self.pending_by_id:
            del self.pending_by_id[request_id]
            self._save_state()
            return True
        return False

    def validate_token(
        self,
        device_id: str,
        token: str,
        role: str | None = None,
        required_scopes: list[str] | None = None,
    ) -> tuple[bool, str | None]:
        """
        Validate device token.

        Args:
            device_id: Device ID
            token: Token to validate
            role: Expected role
            required_scopes: Required scopes

        Returns:
            (is_valid, error_reason)
        """
        device = self.paired_by_device_id.get(device_id)
        if not device:
            return False, "device-not-paired"

        # Check role
        if role and role not in device.tokens:
            return False, "role-missing"

        # Find matching token
        token_obj = None
        for t in device.tokens.values():
            if t.token == token:
                token_obj = t
                break

        if not token_obj:
            return False, "token-missing"

        if token_obj.is_revoked():
            return False, "token-revoked"

        if role and token_obj.role != role:
            return False, "token-mismatch"

        # Check scopes
        if required_scopes:
            if not all(s in token_obj.scopes for s in required_scopes):
                return False, "scope-mismatch"

        # Update last used
        token_obj.last_used_at_ms = int(time.time() * 1000)
        self._save_state()

        return True, None

    def revoke_token(self, device_id: str, role: str) -> bool:
        """
        Revoke a device token.

        Args:
            device_id: Device ID
            role: Role

        Returns:
            True if revoked, False if not found
        """
        device = self.paired_by_device_id.get(device_id)
        if not device or role not in device.tokens:
            return False

        device.tokens[role].revoked_at_ms = int(time.time() * 1000)
        self._save_state()
        return True

    def unpair_device(self, device_id: str) -> bool:
        """
        Unpair a device.

        Args:
            device_id: Device ID

        Returns:
            True if unpaired, False if not found
        """
        if device_id in self.paired_by_device_id:
            del self.paired_by_device_id[device_id]
            self._save_state()
            return True
        return False

    def list_pending(self) -> list[DevicePairingRequest]:
        """List pending pairing requests."""
        # Clean expired
        now = int(time.time() * 1000)
        expired = [
            req_id
            for req_id, req in self.pending_by_id.items()
            if now - req.ts > self.PENDING_TTL_MS
        ]
        for req_id in expired:
            del self.pending_by_id[req_id]

        if expired:
            self._save_state()

        return list(self.pending_by_id.values())

    def list_paired(self) -> list[PairedDevice]:
        """List paired devices."""
        return list(self.paired_by_device_id.values())

    def _generate_token(self) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)
