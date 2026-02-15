"""
Device authentication token management.

This module manages authentication tokens for paired devices:
- Token creation on device pairing
- Token rotation for security
- Token revocation on unpair
- Token validation

Reference: openclaw/src/gateway/server-methods/device.ts
"""
from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class DeviceToken:
    """Device authentication token"""
    
    token: str
    deviceId: str
    role: str  # "operator" or "node"
    scopes: list[str]
    created_at: float
    expires_at: float | None = None  # No expiry by default
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "token": self.token,
            "deviceId": self.deviceId,
            "role": self.role,
            "scopes": self.scopes,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


class TokenManager:
    """
    Manage device authentication tokens.
    
    This manager handles:
    - Token creation for paired devices
    - Token validation
    - Token rotation for security
    - Token revocation
    - Persistence to disk
    
    Usage:
        manager = TokenManager(config_path)
        
        # Create token on device pairing
        token = manager.create_token(
            device_id="device_123",
            role="operator",
            scopes=["operator.read", "operator.write"]
        )
        
        # Validate token
        device_token = manager.validate_token(token)
        if device_token and not device_token.is_expired():
            # Token is valid
            pass
        
        # Rotate token
        new_token = manager.rotate_token("device_123")
        
        # Revoke token
        manager.revoke_token(token)
    """
    
    def __init__(self, config_path: Path):
        """
        Initialize token manager.
        
        Args:
            config_path: Path to tokens.json file
        """
        self._config_path = config_path
        self._tokens: dict[str, DeviceToken] = {}  # token -> DeviceToken
        self._device_tokens: dict[str, str] = {}  # deviceId -> token
        self._load_tokens()
    
    def _load_tokens(self) -> None:
        """Load tokens from config file"""
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r') as f:
                    data = json.load(f)
                    tokens = data.get('tokens', [])
                    for token_data in tokens:
                        token = DeviceToken(**token_data)
                        self._tokens[token.token] = token
                        self._device_tokens[token.deviceId] = token.token
            except Exception:
                pass
    
    def _save_tokens(self) -> None:
        """Save tokens to config file"""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            'tokens': [token.to_dict() for token in self._tokens.values()]
        }
        with open(self._config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_token(
        self, 
        device_id: str, 
        role: str, 
        scopes: list[str],
        expires_in_days: int | None = None
    ) -> str:
        """
        Create new device token.
        
        Args:
            device_id: Device ID
            role: Device role
            scopes: Device scopes
            expires_in_days: Optional expiration in days
            
        Returns:
            Generated token string
        """
        # Revoke existing token if any
        existing_token = self._device_tokens.get(device_id)
        if existing_token:
            self.revoke_token(existing_token)
        
        # Generate new token
        token_str = secrets.token_urlsafe(32)
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 24 * 60 * 60)
        
        # Create token
        token = DeviceToken(
            token=token_str,
            deviceId=device_id,
            role=role,
            scopes=scopes,
            created_at=time.time(),
            expires_at=expires_at
        )
        
        self._tokens[token_str] = token
        self._device_tokens[device_id] = token_str
        self._save_tokens()
        
        return token_str
    
    def validate_token(self, token_str: str) -> DeviceToken | None:
        """
        Validate token and return device token if valid.
        
        Args:
            token_str: Token string
            
        Returns:
            DeviceToken if valid and not expired, None otherwise
        """
        token = self._tokens.get(token_str)
        if not token:
            return None
        
        if token.is_expired():
            # Clean up expired token
            self.revoke_token(token_str)
            return None
        
        return token
    
    def rotate_token(self, device_id: str) -> str:
        """
        Rotate device token (create new, revoke old).
        
        Args:
            device_id: Device ID
            
        Returns:
            New token string
            
        Raises:
            KeyError: If device has no existing token
        """
        old_token_str = self._device_tokens.get(device_id)
        if not old_token_str:
            raise KeyError(f"No token found for device {device_id}")
        
        old_token = self._tokens[old_token_str]
        
        # Create new token with same role/scopes
        return self.create_token(
            device_id,
            old_token.role,
            old_token.scopes
        )
    
    def revoke_token(self, token_str: str) -> bool:
        """
        Revoke device token.
        
        Args:
            token_str: Token to revoke
            
        Returns:
            True if token was found and revoked, False otherwise
        """
        token = self._tokens.pop(token_str, None)
        if token:
            # Remove from device mapping
            if self._device_tokens.get(token.deviceId) == token_str:
                del self._device_tokens[token.deviceId]
            
            self._save_tokens()
            return True
        
        return False
    
    def get_token_by_device(self, device_id: str) -> DeviceToken | None:
        """
        Get token for device.
        
        Args:
            device_id: Device ID
            
        Returns:
            Device token if found, None otherwise
        """
        token_str = self._device_tokens.get(device_id)
        return self._tokens.get(token_str) if token_str else None
    
    def list_tokens(self) -> list[DeviceToken]:
        """
        List all tokens.
        
        Returns:
            List of device tokens
        """
        return list(self._tokens.values())
    
    def cleanup_expired(self) -> int:
        """
        Remove expired tokens.
        
        Returns:
            Number of tokens removed
        """
        expired = [
            token_str for token_str, token in self._tokens.items()
            if token.is_expired()
        ]
        
        for token_str in expired:
            self.revoke_token(token_str)
        
        return len(expired)


__all__ = [
    "DeviceToken",
    "TokenManager",
]
