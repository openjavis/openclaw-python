"""
Thinking mode enumeration
"""

from enum import Enum


class ThinkingMode(str, Enum):
    """
    Thinking mode for AI reasoning extraction

    - OFF: Don't extract thinking, treat as regular text
    - ON: Extract thinking and include in final response
    - STREAM: Extract thinking and stream separately
    """

    OFF = "off"
    ON = "on"
    STREAM = "stream"
