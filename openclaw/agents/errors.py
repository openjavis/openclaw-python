"""
Error handling and recovery for agent system
"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"  # Minor issues, can continue
    MEDIUM = "medium"  # Significant issues, may need retry
    HIGH = "high"  # Serious issues, likely to fail
    CRITICAL = "critical"  # Fatal errors, cannot continue


class ErrorCategory(Enum):
    """Error categories for classification"""

    NETWORK = "network"  # Network/connection errors
    AUTH = "auth"  # Authentication/authorization errors
    RATE_LIMIT = "rate_limit"  # Rate limiting errors
    CONTEXT_OVERFLOW = "context"  # Context window overflow
    TIMEOUT = "timeout"  # Timeout errors
    VALIDATION = "validation"  # Input validation errors
    PROVIDER = "provider"  # Provider-specific errors
    UNKNOWN = "unknown"  # Unknown/unclassified errors


class AgentError(Exception):
    """Base exception for agent errors"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.retryable = retryable


class ContextOverflowError(AgentError):
    """Context window overflow error"""

    def __init__(self, message: str, used_tokens: int, max_tokens: int):
        super().__init__(
            message=message,
            category=ErrorCategory.CONTEXT_OVERFLOW,
            severity=ErrorSeverity.HIGH,
            details={"used_tokens": used_tokens, "max_tokens": max_tokens},
            retryable=True,  # Can retry with context compression
        )
        self.used_tokens = used_tokens
        self.max_tokens = max_tokens


class RateLimitError(AgentError):
    """Rate limit exceeded error"""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            details={"retry_after": retry_after},
            retryable=True,
        )
        self.retry_after = retry_after


class AuthenticationError(AgentError):
    """Authentication error"""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            category=ErrorCategory.AUTH,
            severity=ErrorSeverity.CRITICAL,
            retryable=False,
        )


class NetworkError(AgentError):
    """Network/connection error"""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            retryable=True,
        )


class TimeoutError(AgentError):
    """Operation timeout error"""

    def __init__(self, message: str, timeout_seconds: float):
        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            details={"timeout_seconds": timeout_seconds},
            retryable=True,
        )


def classify_error(error: Exception) -> ErrorCategory:
    """
    Classify an exception into an error category

    Args:
        error: Exception to classify

    Returns:
        ErrorCategory
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Check for specific error patterns
    if "rate" in error_str and "limit" in error_str:
        return ErrorCategory.RATE_LIMIT

    if any(word in error_str for word in ["auth", "unauthorized", "forbidden", "api key"]):
        return ErrorCategory.AUTH

    if any(word in error_str for word in ["timeout", "timed out"]):
        return ErrorCategory.TIMEOUT

    if any(word in error_str for word in ["context", "token", "too long"]):
        return ErrorCategory.CONTEXT_OVERFLOW

    if any(word in error_str for word in ["network", "connection", "unreachable"]):
        return ErrorCategory.NETWORK

    if "validation" in error_str or "invalid" in error_str:
        return ErrorCategory.VALIDATION

    # Check error type
    if "timeout" in error_type:
        return ErrorCategory.TIMEOUT

    if any(word in error_type for word in ["connection", "network"]):
        return ErrorCategory.NETWORK

    return ErrorCategory.UNKNOWN


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable

    Args:
        error: Exception to check

    Returns:
        True if error is retryable
    """
    if isinstance(error, AgentError):
        return error.retryable

    category = classify_error(error)

    # These categories are generally retryable
    retryable_categories = {
        ErrorCategory.NETWORK,
        ErrorCategory.RATE_LIMIT,
        ErrorCategory.TIMEOUT,
        ErrorCategory.CONTEXT_OVERFLOW,
    }

    return category in retryable_categories


def get_error_severity(error: Exception) -> ErrorSeverity:
    """
    Get severity level for an error

    Args:
        error: Exception to evaluate

    Returns:
        ErrorSeverity
    """
    if isinstance(error, AgentError):
        return error.severity

    category = classify_error(error)

    # Map categories to severities
    severity_map = {
        ErrorCategory.AUTH: ErrorSeverity.CRITICAL,
        ErrorCategory.CONTEXT_OVERFLOW: ErrorSeverity.HIGH,
        ErrorCategory.RATE_LIMIT: ErrorSeverity.MEDIUM,
        ErrorCategory.TIMEOUT: ErrorSeverity.MEDIUM,
        ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
        ErrorCategory.VALIDATION: ErrorSeverity.LOW,
        ErrorCategory.PROVIDER: ErrorSeverity.MEDIUM,
        ErrorCategory.UNKNOWN: ErrorSeverity.MEDIUM,
    }

    return severity_map.get(category, ErrorSeverity.MEDIUM)


def format_error_message(error: Exception) -> str:
    """
    Format error message for user display

    Args:
        error: Exception to format

    Returns:
        Formatted error message
    """
    if isinstance(error, AgentError):
        return f"[{error.category.value}] {error.message}"

    category = classify_error(error)
    return f"[{category.value}] {str(error)}"


class ErrorRecovery:
    """Helper for error recovery strategies"""

    @staticmethod
    async def retry_with_backoff(
        func, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0
    ):
        """
        Retry function with exponential backoff

        Args:
            func: Async function to retry
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        import asyncio

        last_error = None
        delay = base_delay

        for attempt in range(max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_error = e

                if not is_retryable_error(e):
                    logger.error(f"Non-retryable error: {e}")
                    raise

                if attempt < max_retries:
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, max_delay)
                else:
                    logger.error(f"All {max_retries + 1} attempts failed")

        raise last_error
