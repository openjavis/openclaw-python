"""Telegram message sending implementation.

Matches TypeScript src/telegram/send.ts
Provides complete Telegram Bot API message sending functionality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Telegram API limits
TELEGRAM_MAX_TEXT_LENGTH = 4096
TELEGRAM_MAX_CAPTION_LENGTH = 1024
TELEGRAM_MAX_CALLBACK_DATA_LENGTH = 64

# Error patterns
PARSE_ERROR_PATTERNS = [
    "can't parse entities",
    "parse entities",
    "find end of the entity",
]
CHAT_NOT_FOUND_PATTERN = "chat not found"
VOICE_FORBIDDEN_PATTERN = "VOICE_MESSAGES_FORBIDDEN"


@dataclass
class TelegramSendOptions:
    """Options for sending Telegram messages."""

    token: Optional[str] = None
    account_id: Optional[str] = None
    verbose: bool = False
    media_url: Optional[str] = None
    max_bytes: Optional[int] = None
    text_mode: str = "markdown"  # "markdown" or "html"
    plain_text: Optional[str] = None
    as_voice: bool = False
    silent: bool = False
    reply_to_message_id: Optional[int] = None
    quote_text: Optional[str] = None
    message_thread_id: Optional[int] = None
    buttons: Optional[list[list[dict[str, str]]]] = None


@dataclass
class TelegramSendResult:
    """Result of sending a Telegram message."""

    message_id: str
    chat_id: str


@dataclass
class TelegramReactionOptions:
    """Options for Telegram reactions."""

    token: Optional[str] = None
    account_id: Optional[str] = None
    remove: bool = False
    verbose: bool = False


@dataclass
class TelegramDeleteOptions:
    """Options for deleting Telegram messages."""

    token: Optional[str] = None
    account_id: Optional[str] = None
    verbose: bool = False


@dataclass
class TelegramEditOptions:
    """Options for editing Telegram messages."""

    token: Optional[str] = None
    account_id: Optional[str] = None
    verbose: bool = False
    text_mode: str = "markdown"
    buttons: Optional[list[list[dict[str, str]]]] = None


@dataclass
class TelegramStickerOptions:
    """Options for sending Telegram stickers."""

    token: Optional[str] = None
    account_id: Optional[str] = None
    verbose: bool = False
    reply_to_message_id: Optional[int] = None
    message_thread_id: Optional[int] = None


def normalize_chat_id(to: str) -> str:
    """Normalize chat ID for Telegram API.

    Args:
        to: Raw chat ID (can be numeric, @username, or t.me link)

    Returns:
        Normalized chat ID

    Raises:
        ValueError: If chat ID is invalid
    """
    trimmed = to.strip()
    if not trimmed:
        raise ValueError("Recipient is required for Telegram sends")

    # Remove internal prefixes (telegram:, telegram:group:)
    normalized = trimmed
    if normalized.startswith("telegram:group:"):
        normalized = normalized[15:]
    elif normalized.startswith("telegram:"):
        normalized = normalized[9:]

    # Handle t.me links
    if normalized.startswith("https://t.me/") or normalized.startswith("http://t.me/"):
        parts = normalized.split("/")
        if len(parts) >= 4:
            normalized = f"@{parts[-1]}"
    elif normalized.startswith("t.me/"):
        parts = normalized.split("/")
        if len(parts) >= 2:
            normalized = f"@{parts[-1]}"

    if not normalized:
        raise ValueError("Recipient is required for Telegram sends")

    # Already has @ prefix or is numeric
    if normalized.startswith("@"):
        return normalized
    if normalized.lstrip("-").isdigit():
        return normalized

    # Assume it's a username without @
    if len(normalized) >= 5 and normalized.replace("_", "").isalnum():
        return f"@{normalized}"

    return normalized


def normalize_message_id(raw: str | int) -> int:
    """Normalize message ID for Telegram API.

    Args:
        raw: Raw message ID

    Returns:
        Normalized message ID as integer

    Raises:
        ValueError: If message ID is invalid
    """
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        value = raw.strip()
        if not value:
            raise ValueError("Message ID is required for Telegram actions")
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Invalid message ID: {value}")
    raise ValueError("Message ID is required for Telegram actions")


def build_inline_keyboard(
    buttons: Optional[list[list[dict[str, str]]]]
) -> Optional[InlineKeyboardMarkup]:
    """Build inline keyboard markup from button data.

    Args:
        buttons: Button rows, each row is a list of buttons with 'text' and 'callback_data'

    Returns:
        InlineKeyboardMarkup or None if no valid buttons
    """
    if not buttons:
        return None

    rows = []
    for row in buttons:
        button_row = []
        for button in row:
            if not button or "text" not in button or "callback_data" not in button:
                continue
            text = button["text"]
            callback_data = button["callback_data"]
            if not text or not callback_data:
                continue
            # Validate callback_data length (max 64 bytes)
            if len(callback_data.encode("utf-8")) > TELEGRAM_MAX_CALLBACK_DATA_LENGTH:
                logger.warning(
                    f"Callback data too long ({len(callback_data.encode('utf-8'))} bytes), "
                    f"max is {TELEGRAM_MAX_CALLBACK_DATA_LENGTH}"
                )
                continue
            button_row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        if button_row:
            rows.append(button_row)

    if not rows:
        return None

    return InlineKeyboardMarkup(rows)


def _resolve_bot_token(
    explicit_token: Optional[str], config: dict, account_id: Optional[str] = None
) -> str:
    """Resolve bot token from config or explicit value.

    Args:
        explicit_token: Explicitly provided token
        config: Configuration dict
        account_id: Optional account ID

    Returns:
        Bot token

    Raises:
        ValueError: If token not found
    """
    if explicit_token and explicit_token.strip():
        return explicit_token.strip()

    # Try to get from config
    telegram_config = config.get("channels", {}).get("telegram", {})

    if account_id:
        # Try account-specific token
        accounts = telegram_config.get("accounts", {})
        account_config = accounts.get(account_id, {})
        token = account_config.get("botToken") or account_config.get("bot_token")
        if token:
            return token.strip()

    # Try default token
    token = telegram_config.get("botToken") or telegram_config.get("bot_token")
    if token:
        return token.strip()

    # Try environment variable
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        return token.strip()

    account_msg = f' for account "{account_id}"' if account_id else ""
    raise ValueError(
        f"Telegram bot token missing{account_msg}. "
        "Set channels.telegram.botToken or TELEGRAM_BOT_TOKEN environment variable."
    )


def _is_parse_error(error_message: str) -> bool:
    """Check if error is a parse error."""
    error_lower = error_message.lower()
    return any(pattern in error_lower for pattern in PARSE_ERROR_PATTERNS)


def _is_chat_not_found_error(error_message: str) -> bool:
    """Check if error is chat not found."""
    return CHAT_NOT_FOUND_PATTERN in error_message.lower()


def _wrap_chat_not_found_error(err: Exception, chat_id: str, to: str) -> Exception:
    """Wrap chat not found error with helpful message."""
    if _is_chat_not_found_error(str(err)):
        return ValueError(
            f"Telegram send failed: chat not found (chat_id={chat_id}). "
            "Likely: bot not started in DM, bot removed from group/channel, "
            f"group migrated (new -100… id), or wrong bot token. Input was: {to}."
        )
    return err


async def send_message_telegram(
    to: str,
    text: str,
    opts: Optional[TelegramSendOptions] = None,
    config: Optional[dict] = None,
) -> TelegramSendResult:
    """Send a message via Telegram Bot API.

    Supports:
    - Text messages (HTML/Markdown formatting)
    - Media messages (photo, video, audio, voice, document, animation)
    - Inline keyboard buttons
    - Thread replies (reply_to_message_id, message_thread_id)
    - Silent messages
    - Quote text for replies

    Args:
        to: Chat ID or username
        text: Message text or caption
        opts: Send options
        config: Optional configuration dict

    Returns:
        Send result with message_id and chat_id

    Raises:
        ValueError: If parameters are invalid
        TelegramError: If Telegram API call fails
    """
    if opts is None:
        opts = TelegramSendOptions()
    if config is None:
        from openclaw.config.loader import load_config

        config = load_config()

    # Resolve token and normalize chat ID
    token = _resolve_bot_token(opts.token, config, opts.account_id)
    chat_id = normalize_chat_id(to)

    # Create bot instance
    bot = Bot(token=token)

    # Build optional parameters
    kwargs: dict[str, Any] = {}

    # Thread/forum parameters
    if opts.message_thread_id is not None:
        kwargs["message_thread_id"] = opts.message_thread_id

    # Reply parameters
    if opts.reply_to_message_id is not None:
        if opts.quote_text:
            kwargs["reply_parameters"] = {
                "message_id": opts.reply_to_message_id,
                "quote": opts.quote_text,
            }
        else:
            kwargs["reply_to_message_id"] = opts.reply_to_message_id

    # Silent notification
    if opts.silent:
        kwargs["disable_notification"] = True

    # Inline keyboard
    reply_markup = build_inline_keyboard(opts.buttons)

    # Media handling
    if opts.media_url:
        return await _send_media_message(
            bot, chat_id, text, opts.media_url, reply_markup, kwargs, opts, config, to
        )

    # Text-only message
    if not text or not text.strip():
        raise ValueError("Message must be non-empty for Telegram sends")

    if reply_markup:
        kwargs["reply_markup"] = reply_markup

    # Render text based on text_mode
    from openclaw.channels.telegram.formatter import markdown_to_html

    if opts.text_mode == "html":
        html_text = text
    else:
        html_text = markdown_to_html(text)

    try:
        result = await bot.send_message(
            chat_id=chat_id, text=html_text, parse_mode="HTML", **kwargs
        )
        message_id = str(result.message_id)
        resolved_chat_id = str(result.chat_id)

        if opts.verbose:
            logger.info(f"[telegram] Sent message {message_id} to chat {resolved_chat_id}")

        return TelegramSendResult(message_id=message_id, chat_id=resolved_chat_id)

    except TelegramError as e:
        # Handle parse errors by falling back to plain text
        if _is_parse_error(str(e)):
            if opts.verbose:
                logger.warning(f"HTML parse failed, retrying as plain text: {e}")
            fallback_text = opts.plain_text or text
            try:
                result = await bot.send_message(
                    chat_id=chat_id, text=fallback_text, **kwargs
                )
                message_id = str(result.message_id)
                resolved_chat_id = str(result.chat_id)
                return TelegramSendResult(message_id=message_id, chat_id=resolved_chat_id)
            except TelegramError as e2:
                raise _wrap_chat_not_found_error(e2, chat_id, to)

        raise _wrap_chat_not_found_error(e, chat_id, to)


async def _send_media_message(
    bot: Bot,
    chat_id: str,
    text: str,
    media_url: str,
    reply_markup: Optional[InlineKeyboardMarkup],
    kwargs: dict[str, Any],
    opts: TelegramSendOptions,
    config: dict,
    original_to: str,
) -> TelegramSendResult:
    """Send a media message (photo, video, audio, voice, document, animation).

    Args:
        bot: Bot instance
        chat_id: Normalized chat ID
        text: Caption text
        media_url: URL or path to media file
        reply_markup: Inline keyboard markup
        kwargs: Additional parameters
        opts: Send options
        config: Configuration dict
        original_to: Original recipient string for error messages

    Returns:
        Send result

    Raises:
        TelegramError: If send fails
    """
    # Load media
    from openclaw.media.loader import load_web_media
    from openclaw.media.mime import media_kind_from_mime, is_gif_media

    media = await load_web_media(media_url, opts.max_bytes)
    kind = media_kind_from_mime(media.content_type)
    is_gif = is_gif_media(media.content_type, media.file_name)

    file_name = media.file_name
    if not file_name:
        if is_gif:
            file_name = "animation.gif"
        elif kind == "image":
            file_name = "image.jpg"
        elif kind == "video":
            file_name = "video.mp4"
        elif kind == "audio":
            file_name = "audio.ogg"
        else:
            file_name = "file.bin"

    # Split caption if needed (max 1024 chars)
    from openclaw.telegram.caption import split_telegram_caption

    caption_result = split_telegram_caption(text)
    caption = caption_result["caption"]
    follow_up_text = caption_result["follow_up_text"]

    # Render caption as HTML
    from openclaw.channels.telegram.formatter import markdown_to_html

    if caption:
        if opts.text_mode == "html":
            html_caption = caption
        else:
            html_caption = markdown_to_html(caption)
    else:
        html_caption = None

    # Prepare media parameters
    media_kwargs = kwargs.copy()
    if html_caption:
        media_kwargs["caption"] = html_caption
        media_kwargs["parse_mode"] = "HTML"

    # If caption was split, don't add buttons to media (add to follow-up text instead)
    needs_separate_text = bool(follow_up_text)
    if not needs_separate_text and reply_markup:
        media_kwargs["reply_markup"] = reply_markup

    # Send appropriate media type
    try:
        if is_gif:
            result = await bot.send_animation(
                chat_id=chat_id, animation=media.buffer, filename=file_name, **media_kwargs
            )
        elif kind == "image":
            result = await bot.send_photo(
                chat_id=chat_id, photo=media.buffer, filename=file_name, **media_kwargs
            )
        elif kind == "video":
            result = await bot.send_video(
                chat_id=chat_id, video=media.buffer, filename=file_name, **media_kwargs
            )
        elif kind == "audio":
            # Check if should send as voice
            from openclaw.telegram.voice import resolve_telegram_voice_send

            use_voice = resolve_telegram_voice_send(
                wants_voice=opts.as_voice,
                content_type=media.content_type,
                file_name=file_name,
            )
            if use_voice:
                try:
                    result = await bot.send_voice(
                        chat_id=chat_id, voice=media.buffer, filename=file_name, **media_kwargs
                    )
                except TelegramError as e:
                    if VOICE_FORBIDDEN_PATTERN in str(e):
                        logger.warning("Voice messages forbidden, falling back to audio")
                        result = await bot.send_audio(
                            chat_id=chat_id,
                            audio=media.buffer,
                            filename=file_name,
                            **media_kwargs,
                        )
                    else:
                        raise
            else:
                result = await bot.send_audio(
                    chat_id=chat_id, audio=media.buffer, filename=file_name, **media_kwargs
                )
        else:
            result = await bot.send_document(
                chat_id=chat_id, document=media.buffer, filename=file_name, **media_kwargs
            )

        media_message_id = str(result.message_id)
        resolved_chat_id = str(result.chat_id)

        # Send follow-up text if caption was too long
        if needs_separate_text and follow_up_text:
            text_kwargs = kwargs.copy()
            if reply_markup:
                text_kwargs["reply_markup"] = reply_markup

            if opts.text_mode == "html":
                html_text = follow_up_text
            else:
                html_text = markdown_to_html(follow_up_text)

            try:
                text_result = await bot.send_message(
                    chat_id=chat_id, text=html_text, parse_mode="HTML", **text_kwargs
                )
                return TelegramSendResult(
                    message_id=str(text_result.message_id), chat_id=str(text_result.chat_id)
                )
            except TelegramError as e:
                if _is_parse_error(str(e)):
                    logger.warning(f"HTML parse failed for follow-up, using plain text: {e}")
                    text_result = await bot.send_message(
                        chat_id=chat_id, text=follow_up_text, **text_kwargs
                    )
                    return TelegramSendResult(
                        message_id=str(text_result.message_id),
                        chat_id=str(text_result.chat_id),
                    )
                raise

        return TelegramSendResult(message_id=media_message_id, chat_id=resolved_chat_id)

    except TelegramError as e:
        raise _wrap_chat_not_found_error(e, chat_id, original_to)


async def react_message_telegram(
    chat_id: str | int,
    message_id: str | int,
    emoji: str,
    opts: Optional[TelegramReactionOptions] = None,
    config: Optional[dict] = None,
) -> dict[str, bool]:
    """Add or remove a reaction to/from a Telegram message.

    Args:
        chat_id: Chat ID
        message_id: Message ID
        emoji: Emoji for reaction
        opts: Reaction options
        config: Optional configuration dict

    Returns:
        Result dict with 'ok' key

    Raises:
        ValueError: If parameters are invalid
        TelegramError: If Telegram API call fails
    """
    if opts is None:
        opts = TelegramReactionOptions()
    if config is None:
        from openclaw.config.loader import load_config

        config = load_config()

    token = _resolve_bot_token(opts.token, config, opts.account_id)
    normalized_chat_id = normalize_chat_id(str(chat_id))
    normalized_message_id = normalize_message_id(message_id)

    bot = Bot(token=token)

    # Build reaction array
    trimmed_emoji = emoji.strip()
    if opts.remove or not trimmed_emoji:
        reactions = []
    else:
        reactions = [{"type": "emoji", "emoji": trimmed_emoji}]

    try:
        await bot.set_message_reaction(
            chat_id=normalized_chat_id, message_id=normalized_message_id, reaction=reactions
        )
        if opts.verbose:
            action = "Removed" if opts.remove else "Added"
            logger.info(
                f"[telegram] {action} reaction {emoji} on message {normalized_message_id}"
            )
        return {"ok": True}
    except TelegramError as e:
        logger.error(f"Failed to set reaction: {e}")
        raise


async def delete_message_telegram(
    chat_id: str | int,
    message_id: str | int,
    opts: Optional[TelegramDeleteOptions] = None,
    config: Optional[dict] = None,
) -> dict[str, bool]:
    """Delete a Telegram message.

    Args:
        chat_id: Chat ID
        message_id: Message ID
        opts: Delete options
        config: Optional configuration dict

    Returns:
        Result dict with 'ok' key

    Raises:
        ValueError: If parameters are invalid
        TelegramError: If Telegram API call fails
    """
    if opts is None:
        opts = TelegramDeleteOptions()
    if config is None:
        from openclaw.config.loader import load_config

        config = load_config()

    token = _resolve_bot_token(opts.token, config, opts.account_id)
    normalized_chat_id = normalize_chat_id(str(chat_id))
    normalized_message_id = normalize_message_id(message_id)

    bot = Bot(token=token)

    try:
        await bot.delete_message(chat_id=normalized_chat_id, message_id=normalized_message_id)
        if opts.verbose:
            logger.info(f"[telegram] Deleted message {normalized_message_id}")
        return {"ok": True}
    except TelegramError as e:
        logger.error(f"Failed to delete message: {e}")
        raise


async def edit_message_telegram(
    chat_id: str | int,
    message_id: str | int,
    text: str,
    opts: Optional[TelegramEditOptions] = None,
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """Edit a Telegram message.

    Args:
        chat_id: Chat ID
        message_id: Message ID
        text: New message text
        opts: Edit options
        config: Optional configuration dict

    Returns:
        Result dict with 'ok', 'message_id', and 'chat_id' keys

    Raises:
        ValueError: If parameters are invalid
        TelegramError: If Telegram API call fails
    """
    if opts is None:
        opts = TelegramEditOptions()
    if config is None:
        from openclaw.config.loader import load_config

        config = load_config()

    token = _resolve_bot_token(opts.token, config, opts.account_id)
    normalized_chat_id = normalize_chat_id(str(chat_id))
    normalized_message_id = normalize_message_id(message_id)

    bot = Bot(token=token)

    # Render text
    from openclaw.channels.telegram.formatter import markdown_to_html

    if opts.text_mode == "html":
        html_text = text
    else:
        html_text = markdown_to_html(text)

    # Build reply markup
    # - buttons === None → don't touch buttons (keep existing)
    # - buttons is [] → remove buttons
    # - otherwise → update buttons
    kwargs: dict[str, Any] = {"parse_mode": "HTML"}
    if opts.buttons is not None:
        reply_markup = build_inline_keyboard(opts.buttons)
        if reply_markup:
            kwargs["reply_markup"] = reply_markup
        else:
            # Empty list means remove buttons
            kwargs["reply_markup"] = InlineKeyboardMarkup([])

    try:
        await bot.edit_message_text(
            chat_id=normalized_chat_id, message_id=normalized_message_id, text=html_text, **kwargs
        )
        if opts.verbose:
            logger.info(f"[telegram] Edited message {normalized_message_id}")
        return {"ok": True, "message_id": str(normalized_message_id), "chat_id": normalized_chat_id}
    except TelegramError as e:
        # Handle parse errors by falling back to plain text
        if _is_parse_error(str(e)):
            if opts.verbose:
                logger.warning(f"HTML parse failed, retrying as plain text: {e}")
            try:
                await bot.edit_message_text(
                    chat_id=normalized_chat_id,
                    message_id=normalized_message_id,
                    text=text,
                    **kwargs,
                )
                return {
                    "ok": True,
                    "message_id": str(normalized_message_id),
                    "chat_id": normalized_chat_id,
                }
            except TelegramError:
                raise
        raise


async def send_sticker_telegram(
    to: str,
    file_id: str,
    opts: Optional[TelegramStickerOptions] = None,
    config: Optional[dict] = None,
) -> TelegramSendResult:
    """Send a sticker to a Telegram chat by file_id.

    Args:
        to: Chat ID or username
        file_id: Telegram file_id of the sticker
        opts: Sticker options
        config: Optional configuration dict

    Returns:
        Send result with message_id and chat_id

    Raises:
        ValueError: If parameters are invalid
        TelegramError: If Telegram API call fails
    """
    if not file_id or not file_id.strip():
        raise ValueError("Telegram sticker file_id is required")

    if opts is None:
        opts = TelegramStickerOptions()
    if config is None:
        from openclaw.config.loader import load_config

        config = load_config()

    token = _resolve_bot_token(opts.token, config, opts.account_id)
    chat_id = normalize_chat_id(to)

    bot = Bot(token=token)

    kwargs: dict[str, Any] = {}
    if opts.message_thread_id is not None:
        kwargs["message_thread_id"] = opts.message_thread_id
    if opts.reply_to_message_id is not None:
        kwargs["reply_to_message_id"] = opts.reply_to_message_id

    try:
        result = await bot.send_sticker(chat_id=chat_id, sticker=file_id.strip(), **kwargs)
        message_id = str(result.message_id)
        resolved_chat_id = str(result.chat_id)

        if opts.verbose:
            logger.info(f"[telegram] Sent sticker to chat {resolved_chat_id}")

        return TelegramSendResult(message_id=message_id, chat_id=resolved_chat_id)

    except TelegramError as e:
        raise _wrap_chat_not_found_error(e, chat_id, to)


@dataclass
class TelegramMediaGroupOptions:
    """Options for sending Telegram media groups."""

    token: Optional[str] = None
    account_id: Optional[str] = None
    verbose: bool = False
    caption: Optional[str] = None
    reply_to_message_id: Optional[int] = None
    message_thread_id: Optional[int] = None
    max_bytes: Optional[int] = None


async def send_media_group_telegram(
    to: str,
    media_urls: list[str],
    opts: Optional[TelegramMediaGroupOptions] = None,
    config: Optional[dict] = None,
) -> dict[str, Any]:
    """Send multiple media items as an album (media group).

    Telegram supports 2-10 media items in a group. All items must be photos or videos.

    Args:
        to: Chat ID or username
        media_urls: List of media URLs (2-10 items)
        opts: Media group options
        config: Optional configuration dict

    Returns:
        Dict with 'ok', 'message_ids', and 'chat_id' keys

    Raises:
        ValueError: If parameters are invalid
        TelegramError: If Telegram API call fails
    """
    from telegram import InputMediaPhoto, InputMediaVideo

    if opts is None:
        opts = TelegramMediaGroupOptions()
    if config is None:
        from openclaw.config.loader import load_config

        config = load_config()

    if not media_urls or len(media_urls) < 2:
        raise ValueError("Media group requires at least 2 media items")
    if len(media_urls) > 10:
        logger.warning("Telegram media group limited to 10 items, truncating")
        media_urls = media_urls[:10]

    token = _resolve_bot_token(opts.token, config, opts.account_id)
    chat_id = normalize_chat_id(to)

    bot = Bot(token=token)

    # Load and prepare media
    from openclaw.media.loader import load_web_media
    from openclaw.media.mime import media_kind_from_mime
    from openclaw.channels.telegram.formatter import markdown_to_html

    media_group = []

    for idx, media_url in enumerate(media_urls):
        try:
            media = await load_web_media(media_url, opts.max_bytes)
            kind = media_kind_from_mime(media.content_type)

            # Only first item gets caption
            caption_html = None
            if idx == 0 and opts.caption:
                caption_html = markdown_to_html(opts.caption)
                # Telegram media group captions have same 1024 char limit
                if len(caption_html) > TELEGRAM_MAX_CAPTION_LENGTH:
                    caption_html = caption_html[:TELEGRAM_MAX_CAPTION_LENGTH]

            if kind == "image":
                media_group.append(
                    InputMediaPhoto(media=media.buffer, caption=caption_html, parse_mode="HTML")
                )
            elif kind == "video":
                media_group.append(
                    InputMediaVideo(media=media.buffer, caption=caption_html, parse_mode="HTML")
                )
            else:
                logger.warning(
                    f"Media group only supports photos and videos, skipping {kind}: {media_url}"
                )
                continue

        except Exception as e:
            logger.error(f"Failed to load media {media_url}: {e}")
            continue

    if len(media_group) < 2:
        raise ValueError("Media group requires at least 2 valid photos or videos")

    # Send media group
    kwargs: dict[str, Any] = {}
    if opts.message_thread_id is not None:
        kwargs["message_thread_id"] = opts.message_thread_id
    if opts.reply_to_message_id is not None:
        kwargs["reply_to_message_id"] = opts.reply_to_message_id

    try:
        messages = await bot.send_media_group(chat_id=chat_id, media=media_group, **kwargs)
        message_ids = [str(msg.message_id) for msg in messages]
        resolved_chat_id = str(messages[0].chat_id) if messages else chat_id

        if opts.verbose:
            logger.info(
                f"[telegram] Sent media group with {len(messages)} items to chat {resolved_chat_id}"
            )

        return {
            "ok": True,
            "message_ids": message_ids,
            "chat_id": resolved_chat_id,
            "count": len(messages),
        }

    except TelegramError as e:
        raise _wrap_chat_not_found_error(e, chat_id, to)
