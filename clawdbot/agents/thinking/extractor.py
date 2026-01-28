"""
Extract thinking/reasoning from AI responses
"""

import re
from typing import NamedTuple


class ThinkingContent(NamedTuple):
    """Extracted thinking and regular content"""

    thinking: str  # Content inside thinking tags
    content: str  # Regular content outside tags
    has_thinking: bool  # Whether thinking was found


class ThinkingExtractor:
    """
    Extract thinking/reasoning content from AI responses

    Supports various thinking tag formats:
    - <thinking>...</thinking>
    - <thought>...</thought>
    - <antthinking>...</antthinking>
    """

    # Regex patterns for thinking tags
    THINKING_PATTERN = re.compile(
        r"<\s*(?:think(?:ing)?|thought|antthinking)\s*>(.*?)</\s*(?:think(?:ing)?|thought|antthinking)\s*>",
        re.DOTALL | re.IGNORECASE,
    )

    THINKING_TAG_SCAN = re.compile(
        r"<\s*(/?)(?:think(?:ing)?|thought|antthinking)\s*>", re.IGNORECASE
    )

    def extract(self, text: str) -> ThinkingContent:
        """
        Extract thinking content from text

        Args:
            text: Input text possibly containing thinking tags

        Returns:
            ThinkingContent with thinking and regular content separated
        """
        if not text or not self._has_thinking_tags(text):
            return ThinkingContent(thinking="", content=text, has_thinking=False)

        # Extract all thinking blocks
        thinking_parts = []
        for match in self.THINKING_PATTERN.finditer(text):
            thinking_parts.append(match.group(1).strip())

        # Remove thinking tags and their content
        content = self.THINKING_PATTERN.sub("", text).strip()

        # Join multiple thinking blocks
        thinking = "\n\n".join(thinking_parts) if thinking_parts else ""

        return ThinkingContent(
            thinking=thinking, content=content, has_thinking=bool(thinking_parts)
        )

    def _has_thinking_tags(self, text: str) -> bool:
        """Check if text contains thinking tags"""
        return bool(self.THINKING_TAG_SCAN.search(text))

    def extract_streaming(self, delta: str, state: dict) -> tuple[str, str]:
        """
        Extract thinking from streaming delta

        Args:
            delta: New text delta
            state: Stateful accumulator (modified in-place)

        Returns:
            (thinking_delta, content_delta) tuple
        """
        # Initialize state if needed
        if "buffer" not in state:
            state["buffer"] = ""
            state["in_thinking"] = False
            state["thinking_start"] = 0

        state["buffer"] += delta

        thinking_delta = ""
        content_delta = ""

        # Simple state machine for streaming extraction
        while True:
            if not state["in_thinking"]:
                # Look for opening tag
                match = re.search(
                    r"<\s*(?:think(?:ing)?|thought|antthinking)\s*>", state["buffer"], re.IGNORECASE
                )
                if match:
                    # Found opening tag
                    content_delta += state["buffer"][: match.start()]
                    state["buffer"] = state["buffer"][match.end() :]
                    state["in_thinking"] = True
                    state["thinking_start"] = len(state["buffer"])
                else:
                    # No opening tag, all content
                    content_delta += state["buffer"]
                    state["buffer"] = ""
                    break
            else:
                # Look for closing tag
                match = re.search(
                    r"</\s*(?:think(?:ing)?|thought|antthinking)\s*>",
                    state["buffer"],
                    re.IGNORECASE,
                )
                if match:
                    # Found closing tag
                    thinking_delta += state["buffer"][: match.start()]
                    state["buffer"] = state["buffer"][match.end() :]
                    state["in_thinking"] = False
                else:
                    # No closing tag yet, accumulate
                    if len(state["buffer"]) > 100:  # Release some thinking content
                        thinking_delta += state["buffer"]
                        state["buffer"] = ""
                    break

        return thinking_delta, content_delta
