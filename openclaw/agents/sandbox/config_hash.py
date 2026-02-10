"""Sandbox configuration hashing

Computes hash of sandbox configuration for container reuse.
Matches TypeScript openclaw/src/agents/sandbox/config-hash.ts
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_sandbox_config_hash(config: dict[str, Any]) -> str:
    """
    Compute hash of sandbox configuration
    
    Used to detect configuration changes and determine if
    a hot container can be reused.
    
    Args:
        config: Sandbox configuration dict
        
    Returns:
        Hex string hash of config
    """
    # Sort keys for consistent hashing
    normalized = json.dumps(config, sort_keys=True)
    
    # Compute SHA256
    hash_obj = hashlib.sha256(normalized.encode())
    
    return hash_obj.hexdigest()[:16]  # First 16 chars
