"""Directive extraction from user messages.

Extracts directives like /think, /verbose, /elevated, etc.
Aligned with TypeScript src/auto-reply/reply/directives.ts
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ExtractedDirective:
    """Result of directive extraction."""

    cleaned: str  # Message with directive removed
    has_directive: bool  # Whether directive was found
    raw_level: str | None = None  # Raw level string if provided


@dataclass
class ThinkDirectiveResult(ExtractedDirective):
    """Result of /think directive extraction."""

    think_level: str | None = None


@dataclass
class VerboseDirectiveResult(ExtractedDirective):
    """Result of /verbose directive extraction."""

    verbose_level: str | None = None


@dataclass
class ElevatedDirectiveResult(ExtractedDirective):
    """Result of /elevated directive extraction."""

    elevated_level: str | None = None


@dataclass
class ReasoningDirectiveResult(ExtractedDirective):
    """Result of /reasoning directive extraction."""

    reasoning_level: str | None = None


@dataclass
class NoticeDirectiveResult(ExtractedDirective):
    """Result of /notice directive extraction."""

    notice_level: str | None = None


def escape_regex(value: str) -> str:
    """Escape regex special characters."""
    return re.escape(value)


def match_level_directive(body: str, names: list[str]) -> dict[str, any] | None:
    """Match a level directive in the message body.

    Args:
        body: Message body to search
        names: List of directive names to match

    Returns:
        Dictionary with start, end, and rawLevel if found, None otherwise
    """
    name_pattern = "|".join(escape_regex(name) for name in names)
    pattern = rf"(?:^|\s)/(?:{name_pattern})(?=$|\s|:)"

    match = re.search(pattern, body, re.IGNORECASE)
    if not match:
        return None

    start = match.start()
    end = match.end()

    # Look for optional level argument after ':'
    i = end
    while i < len(body) and body[i].isspace():
        i += 1

    if i < len(body) and body[i] == ":":
        i += 1
        while i < len(body) and body[i].isspace():
            i += 1

    arg_start = i
    while i < len(body) and (body[i].isalpha() or body[i] == "-"):
        i += 1

    raw_level = body[arg_start:i] if i > arg_start else None
    end = i

    return {"start": start, "end": end, "raw_level": raw_level}


def extract_level_directive(
    body: str, names: list[str], normalize_fn: callable | None = None
) -> dict[str, any]:
    """Extract a level directive from message body.

    Args:
        body: Message body
        names: Directive names to match
        normalize_fn: Optional function to normalize the level value

    Returns:
        Dictionary with cleaned text, level, rawLevel, hasDirective
    """
    match = match_level_directive(body, names)
    if not match:
        return {"cleaned": body.strip(), "has_directive": False, "level": None, "raw_level": None}

    raw_level = match["raw_level"]
    level = normalize_fn(raw_level) if normalize_fn and raw_level else raw_level

    # Remove directive from text
    cleaned = body[: match["start"]] + " " + body[match["end"] :]
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return {"cleaned": cleaned, "level": level, "raw_level": raw_level, "has_directive": True}


def extract_simple_directive(body: str, names: list[str]) -> dict[str, any]:
    """Extract a simple directive (no level argument).

    Args:
        body: Message body
        names: Directive names to match

    Returns:
        Dictionary with cleaned text and hasDirective
    """
    name_pattern = "|".join(escape_regex(name) for name in names)
    pattern = rf"(?:^|\s)/(?:{name_pattern})(?=$|\s|:)(?:\s*:\s*)?"

    match = re.search(pattern, body, re.IGNORECASE)
    cleaned = re.sub(pattern, " ", body, flags=re.IGNORECASE) if match else body
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return {"cleaned": cleaned, "has_directive": bool(match)}


def normalize_think_level(raw: str | None) -> str | None:
    """Normalize think level value."""
    if not raw:
        return None

    lower = raw.lower()
    if lower in ("low", "l", "1"):
        return "low"
    elif lower in ("medium", "med", "m", "2"):
        return "medium"
    elif lower in ("high", "h", "3"):
        return "high"

    return raw


def normalize_verbose_level(raw: str | None) -> str | None:
    """Normalize verbose level value."""
    if not raw:
        return None

    lower = raw.lower()
    if lower in ("on", "true", "1", "yes"):
        return "on"
    elif lower in ("off", "false", "0", "no"):
        return "off"

    return raw


def normalize_elevated_level(raw: str | None) -> str | None:
    """Normalize elevated level value."""
    if not raw:
        return None

    lower = raw.lower()
    if lower in ("on", "true", "1", "yes"):
        return "on"
    elif lower in ("off", "false", "0", "no"):
        return "off"

    return raw


def normalize_reasoning_level(raw: str | None) -> str | None:
    """Normalize reasoning level value."""
    if not raw:
        return None

    lower = raw.lower()
    if lower in ("extended", "ext", "on", "true", "1"):
        return "extended"
    elif lower in ("off", "false", "0", "no"):
        return "off"

    return raw


def normalize_notice_level(raw: str | None) -> str | None:
    """Normalize notice level value."""
    if not raw:
        return None

    lower = raw.lower()
    if lower in ("on", "true", "1", "yes"):
        return "on"
    elif lower in ("off", "false", "0", "no"):
        return "off"

    return raw


def extract_think_directive(body: str | None) -> ThinkDirectiveResult:
    """Extract /think or /thinking directive.

    Args:
        body: Message body

    Returns:
        ThinkDirectiveResult with cleaned text and think level
    """
    if not body:
        return ThinkDirectiveResult(cleaned="", has_directive=False)

    result = extract_level_directive(body, ["thinking", "think", "t"], normalize_think_level)

    return ThinkDirectiveResult(
        cleaned=result["cleaned"],
        has_directive=result["has_directive"],
        think_level=result["level"],
        raw_level=result["raw_level"],
    )


def extract_verbose_directive(body: str | None) -> VerboseDirectiveResult:
    """Extract /verbose directive.

    Args:
        body: Message body

    Returns:
        VerboseDirectiveResult with cleaned text and verbose level
    """
    if not body:
        return VerboseDirectiveResult(cleaned="", has_directive=False)

    result = extract_level_directive(body, ["verbose", "v"], normalize_verbose_level)

    return VerboseDirectiveResult(
        cleaned=result["cleaned"],
        has_directive=result["has_directive"],
        verbose_level=result["level"],
        raw_level=result["raw_level"],
    )


def extract_elevated_directive(body: str | None) -> ElevatedDirectiveResult:
    """Extract /elevated directive.

    Args:
        body: Message body

    Returns:
        ElevatedDirectiveResult with cleaned text and elevated level
    """
    if not body:
        return ElevatedDirectiveResult(cleaned="", has_directive=False)

    result = extract_level_directive(body, ["elevated", "elev"], normalize_elevated_level)

    return ElevatedDirectiveResult(
        cleaned=result["cleaned"],
        has_directive=result["has_directive"],
        elevated_level=result["level"],
        raw_level=result["raw_level"],
    )


def extract_reasoning_directive(body: str | None) -> ReasoningDirectiveResult:
    """Extract /reasoning directive.

    Args:
        body: Message body

    Returns:
        ReasoningDirectiveResult with cleaned text and reasoning level
    """
    if not body:
        return ReasoningDirectiveResult(cleaned="", has_directive=False)

    result = extract_level_directive(body, ["reasoning", "reason"], normalize_reasoning_level)

    return ReasoningDirectiveResult(
        cleaned=result["cleaned"],
        has_directive=result["has_directive"],
        reasoning_level=result["level"],
        raw_level=result["raw_level"],
    )


def extract_notice_directive(body: str | None) -> NoticeDirectiveResult:
    """Extract /notice directive.

    Args:
        body: Message body

    Returns:
        NoticeDirectiveResult with cleaned text and notice level
    """
    if not body:
        return NoticeDirectiveResult(cleaned="", has_directive=False)

    result = extract_level_directive(body, ["notice", "notices"], normalize_notice_level)

    return NoticeDirectiveResult(
        cleaned=result["cleaned"],
        has_directive=result["has_directive"],
        notice_level=result["level"],
        raw_level=result["raw_level"],
    )


def extract_status_directive(body: str | None) -> ExtractedDirective:
    """Extract /status directive.

    Args:
        body: Message body

    Returns:
        ExtractedDirective with cleaned text
    """
    if not body:
        return ExtractedDirective(cleaned="", has_directive=False)

    result = extract_simple_directive(body, ["status"])

    return ExtractedDirective(cleaned=result["cleaned"], has_directive=result["has_directive"])
