"""
Thinking/reasoning extraction for models that support extended thinking

This module provides:
- ThinkingLevel enum (off/minimal/low/medium/high/xhigh)
- ThinkingExtractor for parsing thinking blocks
- Streaming and complete extraction support

Models like Claude can output thinking in special blocks.
This extractor separates thinking from regular content.

Matches pi-mono's thinking support but adapted for Python.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ThinkingLevel(str, Enum):
    """
    Thinking/reasoning level for models that support extended reasoning.
    
    Higher levels give model more "thinking budget" for complex reasoning.
    
    Matches Pi Agent's ThinkingLevel enum.
    """
    OFF = "off"  # No extended thinking
    MINIMAL = "minimal"  # Minimal thinking (fastest)
    LOW = "low"  # Low thinking budget
    MEDIUM = "medium"  # Medium thinking budget
    HIGH = "high"  # High thinking budget
    XHIGH = "xhigh"  # Maximum thinking budget (slowest, most thorough)


@dataclass
class ThinkingState:
    """
    State for streaming thinking extraction.
    
    Tracks:
    - Whether we're currently inside a thinking block
    - Accumulated thinking text
    - Buffer for incomplete tags
    """
    in_thinking: bool = False
    thinking_buffer: list[str] = field(default_factory=list)
    tag_buffer: str = ""
    
    def reset(self) -> None:
        """Reset state"""
        self.in_thinking = False
        self.thinking_buffer.clear()
        self.tag_buffer = ""


class ThinkingExtractor:
    """
    Extract thinking blocks from model output.
    
    Supports both:
    - Streaming extraction (process deltas as they arrive)
    - Complete extraction (process full text)
    
    Thinking blocks are typically wrapped in XML-like tags:
    <thinking>reasoning here</thinking>
    
    Example:
        ```python
        extractor = ThinkingExtractor()
        state = ThinkingState()
        
        # Streaming
        for delta in stream:
            thinking_delta, content_delta = extractor.extract_streaming(
                delta, state
            )
            if thinking_delta:
                print(f"Thinking: {thinking_delta}")
            if content_delta:
                print(f"Content: {content_delta}")
        
        # Complete
        thinking, content = extractor.extract_complete(full_text)
        ```
    """
    
    # Tags that indicate thinking blocks
    THINKING_START_TAG = "<thinking>"
    THINKING_END_TAG = "</thinking>"
    
    # Alternative tags (some models may use different formats)
    ALT_TAGS = {
        "start": ["<think>", "<reasoning>", "<thought>"],
        "end": ["</think>", "</reasoning>", "</thought>"]
    }
    
    def __init__(self, custom_tags: tuple[str, str] | None = None):
        """
        Initialize extractor.
        
        Args:
            custom_tags: Optional (start_tag, end_tag) tuple for custom formats
        """
        if custom_tags:
            self.start_tag = custom_tags[0]
            self.end_tag = custom_tags[1]
        else:
            self.start_tag = self.THINKING_START_TAG
            self.end_tag = self.THINKING_END_TAG
    
    def extract_streaming(
        self,
        delta: str,
        state: ThinkingState
    ) -> tuple[str | None, str | None]:
        """
        Extract thinking and content from streaming delta.
        
        This processes text incrementally, handling partial tags.
        
        Args:
            delta: New text delta from stream
            state: Thinking state (mutated)
            
        Returns:
            Tuple of (thinking_delta, content_delta)
            Either or both may be None
            
        Example:
            ```python
            state = ThinkingState()
            
            # Delta 1: "<thin"
            thinking, content = extractor.extract_streaming("<thin", state)
            # Returns: (None, None) - incomplete tag
            
            # Delta 2: "king>I need to"
            thinking, content = extractor.extract_streaming("king>I need to", state)
            # Returns: ("I need to", None) - inside thinking block
            
            # Delta 3: " analyze</thinking>The answer is"
            thinking, content = extractor.extract_streaming(
                " analyze</thinking>The answer is", state
            )
            # Returns: (" analyze", "The answer is") - exited thinking, content starts
            ```
        """
        # Add delta to buffer
        state.tag_buffer += delta
        
        thinking_delta: str | None = None
        content_delta: str | None = None
        
        # Process buffer
        while state.tag_buffer:
            if not state.in_thinking:
                # Look for start tag
                start_pos = state.tag_buffer.find(self.start_tag)
                
                if start_pos == -1:
                    # No start tag found
                    # Check if buffer could be start of tag
                    if self._could_be_tag_start(state.tag_buffer):
                        # Keep buffer as is, wait for more
                        break
                    else:
                        # Not a tag, emit as content
                        content_delta = state.tag_buffer
                        state.tag_buffer = ""
                        break
                else:
                    # Found start tag
                    # Everything before it is content
                    if start_pos > 0:
                        content_delta = state.tag_buffer[:start_pos]
                    
                    # Enter thinking mode
                    state.in_thinking = True
                    state.tag_buffer = state.tag_buffer[start_pos + len(self.start_tag):]
            
            else:
                # Inside thinking block, look for end tag
                end_pos = state.tag_buffer.find(self.end_tag)
                
                if end_pos == -1:
                    # No end tag found
                    # Check if buffer could be start of end tag
                    if self._could_be_tag_start(state.tag_buffer, is_end=True):
                        # Keep buffer, wait for more
                        break
                    else:
                        # Not an end tag, emit as thinking
                        thinking_delta = state.tag_buffer
                        state.thinking_buffer.append(state.tag_buffer)
                        state.tag_buffer = ""
                        break
                else:
                    # Found end tag
                    # Everything before it is thinking
                    if end_pos > 0:
                        thinking_delta = state.tag_buffer[:end_pos]
                        state.thinking_buffer.append(thinking_delta)
                    
                    # Exit thinking mode
                    state.in_thinking = False
                    state.tag_buffer = state.tag_buffer[end_pos + len(self.end_tag):]
        
        return thinking_delta, content_delta
    
    def extract_complete(self, text: str) -> tuple[str, str]:
        """
        Extract thinking and content from complete text.
        
        This is simpler than streaming extraction since we have full text.
        
        Args:
            text: Complete text with potential thinking blocks
            
        Returns:
            Tuple of (thinking, content)
            
        Example:
            ```python
            text = "<thinking>Let me analyze this</thinking>The answer is 42"
            thinking, content = extractor.extract_complete(text)
            # Returns: ("Let me analyze this", "The answer is 42")
            ```
        """
        # Use regex to find all thinking blocks
        pattern = re.escape(self.start_tag) + r"(.*?)" + re.escape(self.end_tag)
        matches = re.findall(pattern, text, re.DOTALL)
        
        # Combine all thinking blocks
        thinking = "\n".join(matches) if matches else ""
        
        # Remove thinking blocks from text to get content
        content = re.sub(pattern, "", text, flags=re.DOTALL)
        
        # Clean up extra whitespace
        thinking = thinking.strip()
        content = content.strip()
        
        return thinking, content
    
    def _could_be_tag_start(self, buffer: str, is_end: bool = False) -> bool:
        """
        Check if buffer could be the start of a tag.
        
        This prevents premature emission when we might be seeing
        the beginning of a tag.
        
        Args:
            buffer: Current buffer
            is_end: Whether checking for end tag
            
        Returns:
            True if buffer could be start of tag
        """
        tag = self.end_tag if is_end else self.start_tag
        
        # Check if tag starts with buffer
        if tag.startswith(buffer):
            return True
        
        # Check alternative tags
        alt_tags = self.ALT_TAGS["end"] if is_end else self.ALT_TAGS["start"]
        for alt_tag in alt_tags:
            if alt_tag.startswith(buffer):
                return True
        
        return False


class ThinkingMode(str, Enum):
    """
    Mode for thinking extraction and presentation.
    
    Different from ThinkingLevel (which controls model behavior).
    This controls how thinking is extracted and presented.
    """
    OFF = "off"  # Don't extract thinking
    ON = "on"  # Extract thinking but don't stream separately
    STREAM = "stream"  # Stream thinking separately from content


def get_thinking_budget(level: ThinkingLevel) -> int | None:
    """
    Get thinking token budget for level.
    
    This maps thinking levels to approximate token budgets.
    Actual implementation depends on model provider.
    
    Args:
        level: Thinking level
        
    Returns:
        Token budget or None for default
    """
    budgets = {
        ThinkingLevel.OFF: 0,
        ThinkingLevel.MINIMAL: 1000,
        ThinkingLevel.LOW: 2000,
        ThinkingLevel.MEDIUM: 4000,
        ThinkingLevel.HIGH: 8000,
        ThinkingLevel.XHIGH: 16000,
    }
    return budgets.get(level, 0)


__all__ = [
    "ThinkingLevel",
    "ThinkingState",
    "ThinkingExtractor",
    "ThinkingMode",
    "get_thinking_budget",
]
