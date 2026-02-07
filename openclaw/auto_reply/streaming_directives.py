"""Streaming directive accumulator.

Handles parsing directives from streaming agent output.
Aligned with TypeScript src/auto-reply/reply/streaming-directives.ts
"""

from __future__ import annotations

from dataclasses import dataclass

from .directive_tags import parse_inline_directives
from .media_parse import split_media_from_output
from .tokens import SILENT_REPLY_TOKEN, is_silent_reply_text


@dataclass
class ReplyDirectiveParseResult:
    """Parsed reply directive result."""

    text: str | None = None
    media_url: str | None = None
    media_urls: list[str] | None = None
    reply_to_id: str | None = None
    reply_to_tag: bool = False
    reply_to_current: bool = False
    audio_as_voice: bool = False
    is_silent: bool = False


@dataclass
class PendingReplyState:
    """State of pending reply directives."""

    explicit_id: str | None = None
    saw_current: bool = False
    has_tag: bool = False


def split_trailing_directive(text: str) -> dict[str, str]:
    """Split trailing incomplete directive from text.

    If text ends with an incomplete [[...]] directive, split it off.

    Args:
        text: Text to split

    Returns:
        Dictionary with 'text' and 'tail' keys
    """
    open_index = text.rfind("[[")
    if open_index < 0:
        return {"text": text, "tail": ""}

    close_index = text.find("]]", open_index + 2)
    if close_index >= 0:
        # Complete directive, no split needed
        return {"text": text, "tail": ""}

    # Incomplete directive at end
    return {"text": text[:open_index], "tail": text[open_index:]}


def parse_chunk(raw: str, silent_token: str = SILENT_REPLY_TOKEN) -> dict:
    """Parse a chunk of output text for directives.

    Args:
        raw: Raw text chunk
        silent_token: Token indicating silent reply

    Returns:
        Dictionary with parsed directives
    """
    # Split media from text
    split = split_media_from_output(raw)
    text = split.text or ""

    # Parse reply directives
    reply_parsed = parse_inline_directives(text, strip_audio_tag=False, strip_reply_tags=True)

    if reply_parsed.has_reply_tag:
        text = reply_parsed.text

    # Check for silent reply
    is_silent = is_silent_reply_text(text, silent_token) or reply_parsed.is_silent
    if is_silent:
        text = ""

    return {
        "text": text,
        "media_urls": split.media_urls,
        "media_url": split.media_url,
        "reply_to_id": reply_parsed.reply_to_id,
        "reply_to_explicit_id": reply_parsed.reply_to_explicit_id,
        "reply_to_current": reply_parsed.reply_to_current,
        "reply_to_tag": reply_parsed.has_reply_tag,
        "audio_as_voice": split.audio_as_voice,
        "is_silent": is_silent,
    }


def has_renderable_content(parsed: dict) -> bool:
    """Check if parsed result has renderable content.

    Args:
        parsed: Parsed directive dictionary

    Returns:
        True if there's content to render
    """
    return bool(
        parsed.get("text")
        or parsed.get("media_url")
        or (parsed.get("media_urls") and len(parsed["media_urls"]) > 0)
        or parsed.get("audio_as_voice")
    )


class StreamingDirectiveAccumulator:
    """Accumulator for streaming directive parsing.

    Handles incremental parsing of directives from streaming output,
    accounting for incomplete directives at chunk boundaries.
    """

    def __init__(self):
        """Initialize accumulator."""
        self.pending_tail = ""
        self.pending_reply = PendingReplyState()

    def reset(self) -> None:
        """Reset accumulator state."""
        self.pending_tail = ""
        self.pending_reply = PendingReplyState()

    def consume(
        self, raw: str, final: bool = False, silent_token: str = SILENT_REPLY_TOKEN
    ) -> ReplyDirectiveParseResult | None:
        """Consume a chunk of text and parse directives.

        Args:
            raw: Raw text chunk
            final: Whether this is the final chunk
            silent_token: Token for silent reply

        Returns:
            ReplyDirectiveParseResult if there's renderable content, None otherwise
        """
        # Combine with pending tail
        combined = f"{self.pending_tail}{raw or ''}"
        self.pending_tail = ""

        # If not final, split off incomplete trailing directive
        if not final:
            split = split_trailing_directive(combined)
            combined = split["text"]
            self.pending_tail = split["tail"]

        if not combined:
            return None

        # Parse the chunk
        parsed = parse_chunk(combined, silent_token)

        # Merge with pending reply state
        has_tag = self.pending_reply.has_tag or parsed["reply_to_tag"]
        saw_current = self.pending_reply.saw_current or parsed["reply_to_current"]
        explicit_id = parsed.get("reply_to_explicit_id") or self.pending_reply.explicit_id

        # Create combined result
        combined_result = ReplyDirectiveParseResult(
            text=parsed.get("text"),
            media_url=parsed.get("media_url"),
            media_urls=parsed.get("media_urls"),
            reply_to_id=explicit_id,
            reply_to_current=saw_current,
            reply_to_tag=has_tag,
            audio_as_voice=parsed.get("audio_as_voice", False),
            is_silent=parsed.get("is_silent", False),
        )

        # Check if we have renderable content
        if not has_renderable_content(parsed.__dict__ if hasattr(parsed, "__dict__") else parsed):
            # Update pending state if we have tags
            if has_tag:
                self.pending_reply = PendingReplyState(
                    explicit_id=explicit_id, saw_current=saw_current, has_tag=has_tag
                )
            return None

        # Reset pending state
        self.pending_reply = PendingReplyState()

        return combined_result


def create_streaming_directive_accumulator() -> StreamingDirectiveAccumulator:
    """Create a new streaming directive accumulator.

    Returns:
        StreamingDirectiveAccumulator instance
    """
    return StreamingDirectiveAccumulator()
