"""Enhanced Telegram channel implementation.

Extends basic Telegram with webhook, reactions, buttons, etc.
"""

from __future__ import annotations

from .inline_buttons import InlineButton, create_inline_keyboard
from .media_upload import MediaUploadResult, upload_media
from .reactions import add_reaction, remove_reaction
from .webhook import TelegramWebhookHandler

__all__ = [
    "TelegramWebhookHandler",
    "add_reaction",
    "remove_reaction",
    "create_inline_keyboard",
    "InlineButton",
    "upload_media",
    "MediaUploadResult",
]
