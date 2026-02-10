"""Core pairing store implementation matching TypeScript openclaw/src/pairing"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .code_generator import generate_pairing_code, normalize_pairing_code
from .storage import PairingStorage
from .types import ChannelPairingAdapter, PairingRequest

logger = logging.getLogger(__name__)

# Request TTL: 1 hour
REQUEST_TTL = timedelta(hours=1)

# Max pending requests per channel
MAX_PENDING_REQUESTS = 3

# Global storage instance
_storage: PairingStorage | None = None


def get_storage() -> PairingStorage:
    """Get or create global storage instance"""
    global _storage
    
    if _storage is None:
        # Default to ~/.openclaw/oauth/
        state_dir = Path.home() / ".openclaw" / "oauth"
        
        # Allow override via environment variable
        if "OPENCLAW_STATE_DIR" in os.environ:
            state_dir = Path(os.environ["OPENCLAW_STATE_DIR"]) / "oauth"
        
        _storage = PairingStorage(state_dir)
    
    return _storage


def upsert_channel_pairing_request(
    channel: str,
    sender_id: str,
    meta: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Create or update pairing request
    
    Args:
        channel: Channel identifier
        sender_id: Sender ID
        meta: Optional metadata
        
    Returns:
        Dict with:
        - code: Pairing code
        - created: True if new request, False if existing
    """
    storage = get_storage()
    
    # Load existing requests
    data = storage.load_pairing_requests(channel)
    requests = data.get("requests", [])
    
    # Clean up expired requests
    requests = _cleanup_expired_requests(requests)
    
    # Check for existing request
    existing_request = None
    for req_data in requests:
        if req_data["id"] == sender_id:
            existing_request = PairingRequest.from_dict(req_data)
            break
    
    if existing_request:
        # Update last seen time
        existing_request.last_seen_at = datetime.now(timezone.utc).isoformat()
        
        # Save updated request
        _update_request_in_list(requests, existing_request)
        data["requests"] = requests
        storage.save_pairing_requests(channel, data)
        
        logger.info(f"Updated existing pairing request for {channel}:{sender_id}")
        
        return {
            "code": existing_request.code,
            "created": False
        }
    
    # Check request limit
    if len(requests) >= MAX_PENDING_REQUESTS:
        # Remove oldest request
        requests.sort(key=lambda r: r["created_at"])
        requests.pop(0)
        logger.warning(f"Removed oldest pairing request (limit: {MAX_PENDING_REQUESTS})")
    
    # Generate new code
    existing_codes = {r["code"] for r in requests}
    code = generate_pairing_code(existing_codes)
    
    # Create new request
    new_request = PairingRequest(
        id=sender_id,
        code=code,
        meta=meta or {}
    )
    
    requests.append(new_request.to_dict())
    data["requests"] = requests
    storage.save_pairing_requests(channel, data)
    
    logger.info(f"Created pairing request for {channel}:{sender_id} with code {code}")
    
    return {
        "code": code,
        "created": True
    }


def approve_channel_pairing_code(
    channel: str,
    code: str,
    adapter: ChannelPairingAdapter | None = None,
) -> dict[str, Any] | None:
    """
    Approve pairing code
    
    Args:
        channel: Channel identifier
        code: Pairing code to approve
        adapter: Optional channel adapter
        
    Returns:
        Dict with approved request info, or None if code not found
    """
    storage = get_storage()
    
    # Normalize code
    code = normalize_pairing_code(code)
    
    # Load requests
    data = storage.load_pairing_requests(channel)
    requests = data.get("requests", [])
    
    # Find request
    approved_request = None
    remaining_requests = []
    
    for req_data in requests:
        if req_data["code"] == code:
            approved_request = PairingRequest.from_dict(req_data)
        else:
            remaining_requests.append(req_data)
    
    if not approved_request:
        logger.warning(f"Pairing code {code} not found for {channel}")
        return None
    
    # Remove from pending requests
    data["requests"] = remaining_requests
    storage.save_pairing_requests(channel, data)
    
    # Add to allowFrom
    entry = approved_request.id
    if adapter:
        entry = adapter.normalize_entry(entry)
    
    add_channel_allow_from_entry(channel, entry)
    
    logger.info(f"Approved pairing request {code} for {channel}:{approved_request.id}")
    
    return {
        "id": approved_request.id,
        "entry": approved_request,
    }


def read_channel_allow_from_store(
    channel: str,
    config_entries: list[str] | None = None,
    adapter: ChannelPairingAdapter | None = None,
) -> list[str]:
    """
    Read allowFrom list for channel
    
    Combines config entries with pairing-approved entries.
    
    Args:
        channel: Channel identifier
        config_entries: Optional entries from config
        adapter: Optional channel adapter
        
    Returns:
        List of allowed sender IDs
    """
    storage = get_storage()
    
    # Load from file
    file_entries = storage.load_allowfrom(channel)
    
    # Combine with config entries
    all_entries = list(config_entries or []) + file_entries
    
    # Normalize if adapter provided
    if adapter:
        all_entries = [adapter.normalize_entry(e) for e in all_entries]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_entries = []
    for entry in all_entries:
        if entry not in seen:
            seen.add(entry)
            unique_entries.append(entry)
    
    return unique_entries


def add_channel_allow_from_entry(
    channel: str,
    entry: str,
    adapter: ChannelPairingAdapter | None = None,
) -> None:
    """
    Add entry to allowFrom list
    
    Args:
        channel: Channel identifier
        entry: Entry to add
        adapter: Optional channel adapter
    """
    storage = get_storage()
    
    # Normalize entry
    if adapter:
        entry = adapter.normalize_entry(entry)
    
    # Load existing entries
    entries = storage.load_allowfrom(channel)
    
    # Add if not already present
    if entry not in entries:
        entries.append(entry)
        storage.save_allowfrom(channel, entries)
        logger.info(f"Added {entry} to {channel} allowFrom")
    else:
        logger.debug(f"Entry {entry} already in {channel} allowFrom")


def remove_channel_allow_from_entry(
    channel: str,
    entry: str,
    adapter: ChannelPairingAdapter | None = None,
) -> bool:
    """
    Remove entry from allowFrom list
    
    Args:
        channel: Channel identifier
        entry: Entry to remove
        adapter: Optional channel adapter
        
    Returns:
        True if entry was removed
    """
    storage = get_storage()
    
    # Normalize entry
    if adapter:
        entry = adapter.normalize_entry(entry)
    
    # Load existing entries
    entries = storage.load_allowfrom(channel)
    
    # Remove if present
    if entry in entries:
        entries.remove(entry)
        storage.save_allowfrom(channel, entries)
        logger.info(f"Removed {entry} from {channel} allowFrom")
        return True
    else:
        logger.debug(f"Entry {entry} not in {channel} allowFrom")
        return False


def list_channel_pairing_requests(channel: str) -> list[PairingRequest]:
    """
    List pending pairing requests for channel
    
    Args:
        channel: Channel identifier
        
    Returns:
        List of pairing requests
    """
    storage = get_storage()
    
    # Load requests
    data = storage.load_pairing_requests(channel)
    requests = data.get("requests", [])
    
    # Clean up expired
    requests = _cleanup_expired_requests(requests)
    
    # Convert to objects
    return [PairingRequest.from_dict(r) for r in requests]


def _cleanup_expired_requests(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove expired requests"""
    now = datetime.now(timezone.utc)
    
    valid_requests = []
    
    for req_data in requests:
        try:
            created_at = datetime.fromisoformat(req_data["created_at"].replace("Z", "+00:00"))
            
            if now - created_at < REQUEST_TTL:
                valid_requests.append(req_data)
            else:
                logger.debug(f"Removed expired request: {req_data['code']}")
        except Exception as e:
            logger.error(f"Error parsing request date: {e}")
            # Keep request if we can't parse date (safe default)
            valid_requests.append(req_data)
    
    return valid_requests


def _update_request_in_list(requests: list[dict[str, Any]], updated_request: PairingRequest) -> None:
    """Update request in list"""
    for i, req_data in enumerate(requests):
        if req_data["id"] == updated_request.id:
            requests[i] = updated_request.to_dict()
            break
