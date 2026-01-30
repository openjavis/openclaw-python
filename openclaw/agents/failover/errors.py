"""
Failover error types
"""

from enum import Enum


class FailoverReason(str, Enum):
    """Reasons for model failover"""

    AUTH = "auth"  # Authentication error
    RATE_LIMIT = "rate_limit"  # Rate limit exceeded
    CONTEXT_OVERFLOW = "context_overflow"  # Context window too large
    TIMEOUT = "timeout"  # Request timeout
    SERVER_ERROR = "server_error"  # Server error (5xx)
    MODEL_ERROR = "model_error"  # Model-specific error
    UNKNOWN = "unknown"  # Unknown error


class FallbackError(Exception):
    """
    Error that triggers model failover

    Attributes:
        message: Error message
        reason: Failover reason
        provider: Current provider
        model: Current model
        original_error: Original exception
    """

    def __init__(
        self,
        message: str,
        reason: FailoverReason = FailoverReason.UNKNOWN,
        provider: str | None = None,
        model: str | None = None,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.reason = reason
        self.provider = provider
        self.model = model
        self.original_error = original_error

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "message": self.message,
            "reason": self.reason.value,
            "provider": self.provider,
            "model": self.model,
            "original_error": str(self.original_error) if self.original_error else None,
        }
