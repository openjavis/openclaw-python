"""
Model fallback chain implementation
"""

import logging
from dataclasses import dataclass
from typing import Any

from .errors import FailoverReason, FallbackError

logger = logging.getLogger(__name__)


@dataclass
class FallbackChain:
    """
    Model fallback configuration

    Attributes:
        primary: Primary model (provider/model format)
        fallbacks: List of fallback models in order
        max_attempts: Maximum number of attempts
    """

    primary: str
    fallbacks: list[str]
    max_attempts: int = 5

    def get_models(self) -> list[str]:
        """Get all models in order (primary + fallbacks)"""
        return [self.primary] + self.fallbacks

    def __len__(self) -> int:
        """Get total number of models"""
        return len(self.fallbacks) + 1


class FallbackManager:
    """
    Manage model fallback logic

    Features:
    - Try models in sequence
    - Track which models have been tried
    - Classify errors for failover decisions
    """

    def __init__(self, chain: FallbackChain | None = None):
        """
        Initialize fallback manager

        Args:
            chain: Fallback chain configuration
        """
        self.chain = chain
        self.current_index = 0
        self.attempts_per_model: dict[str, int] = {}

    def get_current_model(self) -> str:
        """Get current model"""
        if not self.chain:
            raise ValueError("No fallback chain configured")

        models = self.chain.get_models()
        if self.current_index >= len(models):
            raise FallbackError(
                "All models in fallback chain exhausted", reason=FailoverReason.UNKNOWN
            )

        return models[self.current_index]

    def get_next_model(self) -> str | None:
        """
        Get next model in chain

        Returns:
            Next model or None if chain exhausted
        """
        if not self.chain:
            return None

        models = self.chain.get_models()
        self.current_index += 1

        if self.current_index >= len(models):
            return None

        next_model = models[self.current_index]
        logger.info(f"Falling back to model: {next_model}")
        return next_model

    def should_failover(self, error: Exception) -> tuple[bool, FailoverReason]:
        """
        Determine if error should trigger failover

        Args:
            error: Exception that occurred

        Returns:
            (should_failover, reason) tuple
        """
        # Check if it's already a FallbackError
        if isinstance(error, FallbackError):
            return True, error.reason

        error_str = str(error).lower()

        # Authentication errors
        if any(
            keyword in error_str
            for keyword in ["authentication", "unauthorized", "api key", "invalid key", "401"]
        ):
            return True, FailoverReason.AUTH

        # Rate limit errors
        if any(
            keyword in error_str
            for keyword in ["rate limit", "too many requests", "429", "quota exceeded"]
        ):
            return True, FailoverReason.RATE_LIMIT

        # Context overflow
        if any(
            keyword in error_str
            for keyword in ["context length", "maximum context", "too long", "token limit"]
        ):
            return True, FailoverReason.CONTEXT_OVERFLOW

        # Timeout errors
        if any(keyword in error_str for keyword in ["timeout", "timed out", "deadline exceeded"]):
            return True, FailoverReason.TIMEOUT

        # Server errors
        if any(
            keyword in error_str
            for keyword in ["500", "502", "503", "504", "server error", "internal error"]
        ):
            return True, FailoverReason.SERVER_ERROR

        # Model-specific errors
        if any(
            keyword in error_str
            for keyword in ["model not found", "unsupported model", "overloaded"]
        ):
            return True, FailoverReason.MODEL_ERROR

        # Unknown errors - be conservative
        return False, FailoverReason.UNKNOWN

    def record_attempt(self, model: str) -> None:
        """Record an attempt for a model"""
        if model not in self.attempts_per_model:
            self.attempts_per_model[model] = 0
        self.attempts_per_model[model] += 1

    def record_success(self, model: str) -> None:
        """Record successful model usage"""
        logger.info(
            f"Model {model} succeeded after {self.attempts_per_model.get(model, 1)} attempt(s)"
        )

    def reset(self) -> None:
        """Reset to start of chain"""
        self.current_index = 0
        self.attempts_per_model.clear()

    def get_status(self) -> dict[str, Any]:
        """Get fallback status"""
        if not self.chain:
            return {"configured": False}

        return {
            "configured": True,
            "current_model": self.get_current_model(),
            "current_index": self.current_index,
            "total_models": len(self.chain),
            "attempts_per_model": self.attempts_per_model.copy(),
            "chain": self.chain.get_models(),
        }
