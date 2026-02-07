"""Group message gating logic.

Determines whether to process messages in group chats.
Aligned with TypeScript src/web/auto-reply/monitor/group-gating.ts
"""

from __future__ import annotations

from dataclasses import dataclass

from .mentions import has_mention


@dataclass
class GroupGatingResult:
    """Result of group gating check."""

    should_process: bool  # Whether to process this message
    reason: str | None = None  # Reason for decision


class GroupGatingMode:
    """Group gating modes."""

    ALWAYS = "always"  # Always respond in groups
    MENTIONS = "mentions"  # Only respond to mentions
    NEVER = "never"  # Never respond in groups


def check_group_gating(
    message_text: str,
    is_group: bool,
    mode: str = GroupGatingMode.MENTIONS,
    agent_names: list[str] | None = None,
    activation_keywords: list[str] | None = None,
) -> GroupGatingResult:
    """Check if message should be processed in group chat.

    Args:
        message_text: Message text
        is_group: Whether this is a group chat
        mode: Gating mode (always, mentions, never)
        agent_names: Agent names for mention detection
        activation_keywords: Keywords that activate the bot

    Returns:
        GroupGatingResult indicating whether to process
    """
    # If not a group, always process
    if not is_group:
        return GroupGatingResult(should_process=True, reason="not_group")

    # Check mode
    if mode == GroupGatingMode.NEVER:
        return GroupGatingResult(should_process=False, reason="mode_never")

    if mode == GroupGatingMode.ALWAYS:
        return GroupGatingResult(should_process=True, reason="mode_always")

    # Default: mentions mode
    # Check for mentions
    if agent_names and has_mention(message_text, agent_names):
        return GroupGatingResult(should_process=True, reason="mentioned")

    # Check for activation keywords
    if activation_keywords:
        message_lower = message_text.lower()
        for keyword in activation_keywords:
            if keyword.lower() in message_lower:
                return GroupGatingResult(should_process=True, reason="keyword_match")

    return GroupGatingResult(should_process=False, reason="no_mention_or_keyword")


def should_process_group_message(
    message_text: str, is_group: bool, config: dict | None = None
) -> bool:
    """Check if group message should be processed.

    Simplified helper that uses configuration.

    Args:
        message_text: Message text
        is_group: Whether this is a group chat
        config: Optional configuration dict

    Returns:
        True if message should be processed
    """
    if not config:
        config = {}

    mode = config.get("group_mode", GroupGatingMode.MENTIONS)
    agent_names = config.get("agent_names", [])
    activation_keywords = config.get("activation_keywords", [])

    result = check_group_gating(
        message_text=message_text,
        is_group=is_group,
        mode=mode,
        agent_names=agent_names,
        activation_keywords=activation_keywords,
    )

    return result.should_process
