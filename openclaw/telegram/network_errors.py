"""Network error detection for Telegram.

Identifies recoverable network errors for retry logic.
Matches TypeScript src/telegram/network-errors.ts
"""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

TelegramNetworkErrorContext = Literal["polling", "send", "webhook", "unknown"]

# Recoverable error codes
RECOVERABLE_ERROR_CODES = {
    "ECONNRESET",
    "ECONNREFUSED",
    "EPIPE",
    "ETIMEDOUT",
    "ESOCKETTIMEDOUT",
    "ENETUNREACH",
    "EHOSTUNREACH",
    "ENOTFOUND",
    "EAI_AGAIN",
    "ECONNABORTED",
    "ERR_NETWORK",
}

# Recoverable error names
RECOVERABLE_ERROR_NAMES = {
    "AbortError",
    "TimeoutError",
    "ConnectTimeoutError",
    "HeadersTimeoutError",
    "BodyTimeoutError",
    "ConnectionError",
}

# Recoverable message snippets
RECOVERABLE_MESSAGE_SNIPPETS = [
    "fetch failed",
    "network error",
    "network request",
    "socket hang up",
    "timeout",
    "timed out",
    "connection",
    "connect",
]


def _extract_error_code(err: Exception) -> str | None:
    """Extract error code from exception."""
    if hasattr(err, "code"):
        return str(err.code)
    if hasattr(err, "errno"):
        return str(err.errno)
    return None


def _get_error_name(err: Exception) -> str:
    """Get error class name."""
    return err.__class__.__name__


def _collect_error_candidates(err: Exception) -> list[Exception]:
    """Collect error and all nested causes."""
    candidates = [err]
    seen = {id(err)}
    
    current = err
    while True:
        # Check for __cause__ (PEP 3134)
        if hasattr(current, "__cause__") and current.__cause__:
            cause = current.__cause__
            if id(cause) not in seen:
                candidates.append(cause)
                seen.add(id(cause))
                current = cause
                continue
        
        # Check for __context__
        if hasattr(current, "__context__") and current.__context__:
            context = current.__context__
            if id(context) not in seen:
                candidates.append(context)
                seen.add(id(context))
                current = context
                continue
        
        break
    
    return candidates


def is_recoverable_telegram_network_error(
    err: Exception,
    context: TelegramNetworkErrorContext = "unknown",
    allow_message_match: bool = True,
) -> bool:
    """Check if error is a recoverable network error.
    
    Args:
        err: Exception to check
        context: Error context (polling, send, webhook)
        allow_message_match: Allow matching error message text
    
    Returns:
        True if error is recoverable
    """
    if allow_message_match is None:
        allow_message_match = context != "send"
    
    for candidate in _collect_error_candidates(err):
        # Check error code
        code = _extract_error_code(candidate)
        if code and code.upper() in RECOVERABLE_ERROR_CODES:
            return True
        
        # Check error name
        name = _get_error_name(candidate)
        if name in RECOVERABLE_ERROR_NAMES:
            return True
        
        # Check message content
        if allow_message_match:
            message = str(candidate).lower()
            if any(snippet in message for snippet in RECOVERABLE_MESSAGE_SNIPPETS):
                return True
    
    return False
