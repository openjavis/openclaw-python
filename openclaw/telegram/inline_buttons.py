"""Telegram inline buttons scope and configuration.

Matches TypeScript src/telegram/inline-buttons.ts
"""

from __future__ import annotations

from typing import Literal, Optional

InlineButtonsScope = Literal["off", "dm", "group", "all", "allowlist"]


def normalize_inline_buttons_scope(value: any) -> Optional[InlineButtonsScope]:
    """Normalize inline buttons scope value.

    Args:
        value: Raw scope value from config

    Returns:
        Normalized scope or None if invalid
    """
    if not isinstance(value, str):
        return None

    trimmed = value.strip().lower()
    if trimmed in ("off", "dm", "group", "all", "allowlist"):
        return trimmed  # type: ignore

    return None


def resolve_inline_buttons_scope_from_capabilities(
    capabilities: any,
) -> InlineButtonsScope:
    """Resolve inline buttons scope from capabilities config.

    Args:
        capabilities: Capabilities configuration (array or dict)

    Returns:
        Inline buttons scope
    """
    default_scope: InlineButtonsScope = "allowlist"

    if not capabilities:
        return default_scope

    if isinstance(capabilities, list):
        # Array format: check if "inlineButtons" is in the list
        enabled = any(str(entry).strip().lower() == "inlinebuttons" for entry in capabilities)
        return "all" if enabled else "off"

    if isinstance(capabilities, dict):
        # Dict format: check capabilities.inlineButtons
        inline_buttons = capabilities.get("inlineButtons")
        scope = normalize_inline_buttons_scope(inline_buttons)
        return scope if scope else default_scope

    return default_scope


def resolve_telegram_inline_buttons_scope(
    config: dict, account_id: Optional[str] = None
) -> InlineButtonsScope:
    """Resolve inline buttons scope from config.

    Args:
        config: OpenClaw configuration
        account_id: Optional account ID

    Returns:
        Inline buttons scope
    """
    telegram_config = config.get("channels", {}).get("telegram", {})

    if account_id:
        accounts = telegram_config.get("accounts", {})
        account_config = accounts.get(account_id, {})
        capabilities = account_config.get("capabilities")
    else:
        capabilities = telegram_config.get("capabilities")

    return resolve_inline_buttons_scope_from_capabilities(capabilities)


def is_telegram_inline_buttons_enabled(
    config: dict, account_id: Optional[str] = None
) -> bool:
    """Check if inline buttons are enabled for any account.

    Args:
        config: OpenClaw configuration
        account_id: Optional account ID

    Returns:
        True if inline buttons are enabled
    """
    if account_id:
        scope = resolve_telegram_inline_buttons_scope(config, account_id)
        return scope != "off"

    # Check all accounts
    telegram_config = config.get("channels", {}).get("telegram", {})
    accounts = telegram_config.get("accounts", {})

    if not accounts:
        # No multi-account, check default config
        scope = resolve_telegram_inline_buttons_scope(config)
        return scope != "off"

    # Check if any account has buttons enabled
    for acc_id in accounts.keys():
        scope = resolve_telegram_inline_buttons_scope(config, acc_id)
        if scope != "off":
            return True

    return False


def resolve_telegram_target_chat_type(target: str) -> Literal["direct", "group", "unknown"]:
    """Resolve chat type from target string.

    Args:
        target: Target ID or username

    Returns:
        Chat type: "direct", "group", or "unknown"
    """
    trimmed = target.strip()
    if not trimmed:
        return "unknown"

    # Remove common prefixes
    if trimmed.startswith("telegram:group:"):
        trimmed = trimmed[15:]
    elif trimmed.startswith("telegram:"):
        trimmed = trimmed[9:]

    # Chat IDs starting with - are groups
    # Positive IDs are direct chats
    if trimmed.lstrip("-").isdigit():
        return "group" if trimmed.startswith("-") else "direct"

    return "unknown"
