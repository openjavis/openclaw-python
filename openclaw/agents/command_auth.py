"""
Command authorization and owner verification

Matches TypeScript src/auto-reply/command-auth.ts
"""
from __future__ import annotations

import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)


class CommandAuthorization(NamedTuple):
    """Result of command authorization (matches TS CommandAuthorization)."""
    provider_id: str | None
    owner_list: list[str]
    sender_id: str | None
    sender_is_owner: bool
    is_authorized_sender: bool
    from_: str | None
    to: str | None


def resolve_sender_candidates(
    sender_id: str | None,
    sender_e164: str | None,
    from_: str | None,
    provider_id: str | None = None,
    account_id: str | None = None,
) -> list[str]:
    """
    Resolve sender candidates for owner matching (matches TS resolveSenderCandidates).
    
    Returns a list of identifiers to check against owner list:
    - Provider-prefixed ID (telegram:123, discord:456)
    - E.164 phone number (+1234567890)
    - From field
    
    Args:
        sender_id: Sender ID from channel
        sender_e164: E.164 phone number
        from_: From field
        provider_id: Channel provider ID
        account_id: Account ID
    
    Returns:
        List of candidate identifiers
    """
    candidates: list[str] = []
    
    # 1. Provider-prefixed sender ID
    if sender_id and provider_id:
        candidates.append(f"{provider_id.lower()}:{sender_id}")
    
    # 2. Plain sender ID
    if sender_id:
        candidates.append(sender_id)
    
    # 3. E.164 phone number
    if sender_e164:
        e164 = sender_e164.strip()
        if e164.startswith("+"):
            candidates.append(e164)
    
    # 4. From field
    if from_:
        from_trimmed = from_.strip()
        if from_trimmed:
            candidates.append(from_trimmed)
    
    return candidates


def resolve_command_authorization(
    sender_id: str | None,
    sender_e164: str | None,
    from_: str | None,
    to: str | None,
    owner_list: list[str],
    enforce_owner_for_commands: bool = False,
    provider_id: str | None = None,
    account_id: str | None = None,
) -> CommandAuthorization:
    """
    Resolve command authorization (simplified version of TS resolveCommandAuthorization).
    
    Logic (matches TS lines 168-269):
    1. Resolve sender candidates
    2. Match against owner list
    3. Determine if sender is owner
    4. Determine if sender is authorized
    
    Args:
        sender_id: Sender identifier
        sender_e164: E.164 phone number
        from_: From field
        to: To field
        owner_list: List of owner identifiers
        enforce_owner_for_commands: Whether to enforce owner-only commands
        provider_id: Channel provider ID
        account_id: Account ID
    
    Returns:
        CommandAuthorization result
    """
    # Resolve sender candidates
    sender_candidates = resolve_sender_candidates(
        sender_id=sender_id,
        sender_e164=sender_e164,
        from_=from_,
        provider_id=provider_id,
        account_id=account_id,
    )
    
    # Check if owner allowlist configured
    allow_all = "*" in owner_list if owner_list else True
    owner_list_configured = len(owner_list) > 0 and not allow_all
    
    # Match sender against owner list
    matched_sender = None
    if owner_list_configured:
        for candidate in sender_candidates:
            if candidate in owner_list:
                matched_sender = candidate
                break
    
    sender_is_owner = matched_sender is not None
    
    # Determine authorization
    # When enforce_owner_for_commands=False, all senders are authorized regardless of owner list
    if not enforce_owner_for_commands:
        is_authorized = True
    elif allow_all:
        # Wildcard allowlist
        is_authorized = True
    elif owner_list_configured:
        # Explicit owner list with enforcement enabled
        is_authorized = sender_is_owner
    else:
        # Default: allow
        is_authorized = True
    
    # Resolve final sender ID
    final_sender_id = matched_sender if matched_sender else (sender_candidates[0] if sender_candidates else None)
    
    return CommandAuthorization(
        provider_id=provider_id,
        owner_list=owner_list,
        sender_id=final_sender_id,
        sender_is_owner=sender_is_owner,
        is_authorized_sender=is_authorized,
        from_=from_,
        to=to,
    )


def check_owner_permission(
    sender_id: str | None,
    sender_e164: str | None,
    owner_list: list[str],
    provider_id: str | None = None,
) -> bool:
    """
    Simple owner check (quick utility).
    
    Args:
        sender_id: Sender ID
        sender_e164: E.164 phone number
        owner_list: Owner list
        provider_id: Provider ID
    
    Returns:
        True if sender is owner
    """
    if "*" in owner_list:
        return True
    
    candidates = resolve_sender_candidates(
        sender_id=sender_id,
        sender_e164=sender_e164,
        from_=None,
        provider_id=provider_id,
    )
    
    return any(c in owner_list for c in candidates)
