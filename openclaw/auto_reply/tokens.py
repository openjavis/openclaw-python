"""Token definitions and utilities for Auto-Reply.

Aligned with TypeScript src/auto-reply/tokens.ts
"""

from __future__ import annotations

import re

# Token for heartbeat acknowledgment
HEARTBEAT_TOKEN = "HEARTBEAT_OK"

# Token for silent reply (no response)
SILENT_REPLY_TOKEN = "NO_REPLY"


def escape_regexp(value: str) -> str:
    """Escape special regex characters."""
    return re.escape(value)


def is_silent_reply_text(text: str | None, token: str = SILENT_REPLY_TOKEN) -> bool:
    """Check if text indicates a silent reply.

    Args:
        text: Text to check
        token: Silent reply token (default: NO_REPLY)

    Returns:
        True if text contains the silent reply token
    """
    if not text:
        return False

    escaped = escape_regexp(token)

    # Check prefix: starts with token
    prefix_pattern = rf"^\s*{escaped}(?=$|\W)"
    if re.search(prefix_pattern, text):
        return True

    # Check suffix: ends with token
    suffix_pattern = rf"\b{escaped}\b\W*$"
    return bool(re.search(suffix_pattern, text))
