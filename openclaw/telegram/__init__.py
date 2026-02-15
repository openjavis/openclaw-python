"""Telegram Bot API integration for OpenClaw.

This package provides core Telegram bot functionality including:
- Message sending (text, media, stickers)
- Message reactions, editing, and deletion
- Inline keyboards and buttons
- Webhook and polling support
- Draft streaming
- Sticker caching
"""

from .send import (
    send_message_telegram,
    react_message_telegram,
    delete_message_telegram,
    edit_message_telegram,
    send_sticker_telegram,
    send_media_group_telegram,
)

__all__ = [
    "send_message_telegram",
    "react_message_telegram",
    "delete_message_telegram",
    "edit_message_telegram",
    "send_sticker_telegram",
    "send_media_group_telegram",
]
