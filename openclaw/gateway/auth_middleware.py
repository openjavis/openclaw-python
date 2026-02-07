from __future__ import annotations

from typing import Any

from ..auth.device_pairing import DevicePairingManager
from ..gateway.auth import is_loopback_address
from .auth import AuthMode


class GatewayAuthMiddleware:
    """Simple gateway auth middleware used by tests."""

    def __init__(
        self,
        auth_mode: AuthMode = AuthMode.TOKEN,
        token: str | None = None,
        allow_local_direct: bool = False,
        device_pairing_enabled: bool = False,
        state_dir: str | None = None,
    ) -> None:
        self.auth_mode = auth_mode
        self.token = token
        self.allow_local_direct = allow_local_direct
        self.device_pairing_enabled = device_pairing_enabled
        self.device_manager: DevicePairingManager | None = None

        if self.device_pairing_enabled:
            self.device_manager = DevicePairingManager(state_dir)

    def authenticate_connection(
        self,
        request_token: str | None = None,
        client_ip: str | None = None,
        device_id: str | None = None,
        device_token: str | None = None,
    ) -> tuple[bool, str | None, dict[str, Any]]:
        """Authenticate a gateway connection.

        Returns: (is_authenticated, reason, metadata)
        """
        # Local bypass
        if self.allow_local_direct and is_loopback_address(client_ip):
            return True, None, {"auth_method": "local-direct"}

        # Device token authentication
        if device_id and device_token and self.device_manager:
            ok, reason = self.device_manager.validate_token(device_id, device_token)
            if ok:
                return True, None, {"auth_method": "device", "device_id": device_id}
            return False, reason, {"auth_method": "device"}

        # Token-based auth
        if self.auth_mode == AuthMode.TOKEN:
            if self.token is None:
                return False, "token_missing_config", {"auth_method": "token"}
            if request_token is None:
                return False, "token_missing", {"auth_method": "token"}
            if self.token == request_token:
                return True, None, {"auth_method": "token"}
            return False, "token_mismatch", {"auth_method": "token"}

        # Password mode not used in gateway tests
        return False, "unsupported_auth_mode", {}

    # Device pairing helpers used by tests
    def create_device_pairing_request(
        self,
        device_id: str,
        public_key: str,
        display_name: str | None = None,
        platform: str | None = None,
    ) -> str | None:
        if not self.device_manager:
            return None
        return self.device_manager.create_pairing_request(
            device_id=device_id, public_key=public_key, display_name=display_name, platform=platform
        )

    def list_pending_pairing_requests(self) -> list[dict[str, Any]]:
        if not self.device_manager:
            return []
        return [p.to_dict() for p in self.device_manager.list_pending()]

    def approve_pairing_request(self, request_id: str) -> dict[str, Any] | None:
        if not self.device_manager:
            return None
        paired = self.device_manager.approve_request(request_id)
        if not paired:
            return None

        # Extract a usable token for tests: return first token value
        token = None
        if paired.tokens:
            # tokens is dict[str, DeviceAuthToken]
            for t in paired.tokens.values():
                token = t.token
                break

        return {"device_id": paired.device_id, "token": token}


__all__ = ["GatewayAuthMiddleware"]
