"""Inline directive tag parsing.

Parses [[reply_to:ID]], [[silent]], etc.
Aligned with TypeScript src/utils/directive-tags.ts
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DirectiveParseResult:
    """Result of parsing inline directives."""

    text: str  # Text with directives removed
    has_reply_tag: bool = False
    reply_to_id: str | None = None
    reply_to_explicit_id: str | None = None
    reply_to_current: bool = False
    is_silent: bool = False


def parse_inline_directives(
    text: str, strip_audio_tag: bool = False, strip_reply_tags: bool = True
) -> DirectiveParseResult:
    """Parse inline directive tags from text.

    Supports:
    - [[reply_to:MESSAGE_ID]] - Reply to specific message
    - [[reply_to_current]] - Reply to current message
    - [[silent]] - Silent reply (don't send)

    Args:
        text: Text to parse
        strip_audio_tag: Whether to strip audio tags
        strip_reply_tags: Whether to strip reply tags

    Returns:
        DirectiveParseResult with parsed directives and cleaned text
    """
    if not text:
        return DirectiveParseResult(text="")

    has_reply_tag = False
    reply_to_id: str | None = None
    reply_to_explicit_id: str | None = None
    reply_to_current = False
    is_silent = False
    clean_text = text

    # Check for [[silent]] directive
    silent_pattern = r"\[\[silent\]\]"
    if re.search(silent_pattern, clean_text, re.IGNORECASE):
        is_silent = True
        clean_text = re.sub(silent_pattern, "", clean_text, flags=re.IGNORECASE)

    # Check for [[reply_to_current]] directive
    current_pattern = r"\[\[reply_to_current\]\]"
    if re.search(current_pattern, clean_text, re.IGNORECASE):
        has_reply_tag = True
        reply_to_current = True
        if strip_reply_tags:
            clean_text = re.sub(current_pattern, "", clean_text, flags=re.IGNORECASE)

    # Check for [[reply_to:ID]] directive
    reply_to_pattern = r"\[\[reply_to:([^\]]+)\]\]"
    match = re.search(reply_to_pattern, clean_text, re.IGNORECASE)
    if match:
        has_reply_tag = True
        msg_id = match.group(1).strip()
        reply_to_explicit_id = msg_id
        reply_to_id = msg_id
        if strip_reply_tags:
            clean_text = re.sub(reply_to_pattern, "", clean_text, flags=re.IGNORECASE)

    # Clean up extra whitespace
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    return DirectiveParseResult(
        text=clean_text,
        has_reply_tag=has_reply_tag,
        reply_to_id=reply_to_id,
        reply_to_explicit_id=reply_to_explicit_id,
        reply_to_current=reply_to_current,
        is_silent=is_silent,
    )
