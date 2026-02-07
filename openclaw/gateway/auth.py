from __future__ import annotations

import hmac
import ipaddress
from dataclasses import dataclass
from enum import Enum


class AuthMethod(Enum):
    TOKEN = "TOKEN"
    PASSWORD = "PASSWORD"
    LOCAL_DIRECT = "LOCAL_DIRECT"


class AuthMode(Enum):
    TOKEN = "token"
    PASSWORD = "password"


@dataclass
class AuthResult:
    ok: bool
    method: AuthMethod | None = None
    reason: str | None = None


def safe_equal(a: str | None, b: str | None) -> bool:
    """Timing-safe comparison for strings (handles None)."""
    if a is None or b is None:
        return False
    try:
        return hmac.compare_digest(str(a), str(b))
    except Exception:
        return False


def is_loopback_address(addr: str | None) -> bool:
    """Return True when `addr` is a loopback address (IPv4/IPv6)."""
    if not addr:
        return False
    try:
        ip = ipaddress.ip_address(addr)
        return ip.is_loopback
    except Exception:
        # Handle IPv4-mapped IPv6 like ::ffff:127.0.0.1
        try:
            if addr.startswith("::ffff:"):
                v4 = addr.split(":")[-1]
                ip = ipaddress.ip_address(v4)
                return ip.is_loopback
        except Exception:
            return False
    return False


def authorize_gateway_token(config_token: str | None, request_token: str | None) -> AuthResult:
    if config_token is None:
        return AuthResult(ok=False, method=AuthMethod.TOKEN, reason="token_missing_config")
    if request_token is None:
        return AuthResult(ok=False, method=AuthMethod.TOKEN, reason="token_missing")
    if safe_equal(config_token, request_token):
        return AuthResult(ok=True, method=AuthMethod.TOKEN)
    return AuthResult(ok=False, method=AuthMethod.TOKEN, reason="token_mismatch")


def authorize_gateway_password(
    config_password: str | None, request_password: str | None
) -> AuthResult:
    if request_password is None:
        return AuthResult(ok=False, method=AuthMethod.PASSWORD, reason="password_missing")
    if config_password is None:
        return AuthResult(ok=False, method=AuthMethod.PASSWORD, reason="password_missing_config")
    if safe_equal(config_password, request_password):
        return AuthResult(ok=True, method=AuthMethod.PASSWORD)
    return AuthResult(ok=False, method=AuthMethod.PASSWORD, reason="password_mismatch")


def authorize_gateway_connect(
    auth_mode: AuthMode,
    config_token: str | None = None,
    request_token: str | None = None,
    config_password: str | None = None,
    request_password: str | None = None,
    client_ip: str | None = None,
) -> AuthResult:
    # Local loopback bypass
    if is_loopback_address(client_ip):
        return AuthResult(ok=True, method=AuthMethod.LOCAL_DIRECT)

    if auth_mode == AuthMode.TOKEN:
        return authorize_gateway_token(config_token, request_token)
    if auth_mode == AuthMode.PASSWORD:
        return authorize_gateway_password(config_password, request_password)

    return AuthResult(ok=False, method=None, reason="unsupported_auth_mode")


def validate_auth_config(
    auth_mode: AuthMode, config_token: str | None, config_password: str | None
) -> None:
    if auth_mode == AuthMode.TOKEN:
        if not config_token:
            raise ValueError("no token was configured")
    if auth_mode == AuthMode.PASSWORD:
        if not config_password:
            raise ValueError("no password was configured")


__all__ = [
    "AuthMethod",
    "AuthMode",
    "AuthResult",
    "authorize_gateway_connect",
    "authorize_gateway_password",
    "authorize_gateway_token",
    "is_loopback_address",
    "safe_equal",
    "validate_auth_config",
]
