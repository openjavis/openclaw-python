"""Telegram voice message detection.

Determines whether audio should be sent as a voice message vs. regular audio.
Matches TypeScript src/telegram/voice.ts
"""

from __future__ import annotations

from typing import Optional


def resolve_telegram_voice_send(
    text: Optional[str] = None,
    content_type: Optional[str] = None,
    file_name: Optional[str] = None,
) -> bool:
    """Determine if audio should be sent as voice message.
    
    Args:
        text: Associated text/caption
        content_type: MIME type of the audio
        file_name: File name
        
    Returns:
        True if should send as voice message
    """
    # Check for explicit voice request in text
    if text:
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ["voice", "speak", "say", "tell"]):
            # Check if content type is voice-compatible
            if content_type and ("ogg" in content_type or "opus" in content_type or "mpeg" in content_type):
                return True
    
    # Check file name for voice indicators
    if file_name:
        file_lower = file_name.lower()
        if any(ext in file_lower for ext in [".ogg", ".opus", ".oga"]):
            return True
        if "voice" in file_lower or "message" in file_lower:
            return True
    
    # Check content type
    if content_type:
        content_lower = content_type.lower()
        # Voice messages typically use ogg/opus
        if "ogg" in content_lower or "opus" in content_lower:
            # But not if it's clearly a music file
            if file_name and any(music in file_name.lower() for music in ["song", "music", "track", "album"]):
                return False
            return True
    
    # Default to regular audio
    return False


__all__ = ["resolve_telegram_voice_send"]
