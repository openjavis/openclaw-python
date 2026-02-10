"""Channel-based pairing system for messaging platforms

This module provides secure pairing for DM access control across channels.
"""

from .pairing_store import (
    add_channel_allow_from_entry,
    approve_channel_pairing_code,
    read_channel_allow_from_store,
    remove_channel_allow_from_entry,
    upsert_channel_pairing_request,
)
from .types import ChannelPairingAdapter, PairingRequest

__all__ = [
    "PairingRequest",
    "ChannelPairingAdapter",
    "upsert_channel_pairing_request",
    "approve_channel_pairing_code",
    "read_channel_allow_from_store",
    "add_channel_allow_from_entry",
    "remove_channel_allow_from_entry",
]
