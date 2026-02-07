"""Mention detection and processing.

Aligned with TypeScript src/auto-reply/reply/mentions.ts
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class MentionMatch:
    """Detected mention in message."""

    full_match: str  # Full matched text
    agent_id: str | None = None  # Detected agent ID
    is_mention: bool = False  # Whether this is a valid mention


def detect_mentions(text: str, agent_names: list[str] | None = None) -> list[MentionMatch]:
    """Detect @mentions in message text.

    Args:
        text: Message text to search
        agent_names: List of agent names to match (case-insensitive)

    Returns:
        List of detected mentions
    """
    if not text:
        return []

    mentions: list[MentionMatch] = []

    # Pattern for @mentions
    mention_pattern = r"@(\w+)"

    for match in re.finditer(mention_pattern, text):
        full_match = match.group(0)
        username = match.group(1).lower()

        # Check if this mention matches any known agent
        is_valid = False
        agent_id = None

        if agent_names:
            for name in agent_names:
                if username == name.lower():
                    is_valid = True
                    agent_id = name
                    break

        mentions.append(MentionMatch(full_match=full_match, agent_id=agent_id, is_mention=is_valid))

    return mentions


def has_mention(text: str, agent_names: list[str] | None = None) -> bool:
    """Check if text contains valid mention.

    Args:
        text: Message text
        agent_names: Agent names to check for

    Returns:
        True if text contains a valid mention
    """
    mentions = detect_mentions(text, agent_names)
    return any(m.is_mention for m in mentions)


def strip_mentions(text: str) -> str:
    """Remove @mentions from text.

    Args:
        text: Text with mentions

    Returns:
        Text with mentions removed
    """
    return re.sub(r"@\w+", "", text).strip()
