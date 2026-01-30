"""
Rate limiting for API endpoints
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from functools import wraps

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class RateLimitExceeded(HTTPException):
    """Rate limit exceeded exception"""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )


class RateLimiter:
    """
    Token bucket rate limiter

    Example:
        limiter = RateLimiter(requests_per_minute=60)

        @app.get("/api/endpoint")
        async def endpoint(request: Request):
            await limiter.check(request)
            ...
    """

    def __init__(self, requests_per_minute: int = 60, burst_size: int | None = None):
        """
        Initialize rate limiter

        Args:
            requests_per_minute: Requests allowed per minute
            burst_size: Maximum burst size (default: 2x rate)
        """
        self.rate = requests_per_minute
        self.burst_size = burst_size or (requests_per_minute * 2)
        self.window_seconds = 60.0

        # Track requests per identifier (IP, user, API key)
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, identifier: str) -> bool:
        """
        Check if request is allowed

        Args:
            identifier: Unique identifier (IP, user ID, API key)

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Get bucket for this identifier
        bucket = self._buckets[identifier]

        # Remove old entries
        bucket[:] = [t for t in bucket if t > window_start]

        # Check if under limit
        if len(bucket) >= self.rate:
            return False

        # Add this request
        bucket.append(now)
        return True

    def get_retry_after(self, identifier: str) -> int:
        """
        Get retry-after time in seconds

        Args:
            identifier: Unique identifier

        Returns:
            Seconds until next request allowed
        """
        bucket = self._buckets.get(identifier, [])
        if not bucket:
            return 0

        oldest = min(bucket)
        time_until_reset = self.window_seconds - (time.time() - oldest)

        return max(1, int(time_until_reset))

    async def check_request(self, request: Request) -> None:
        """
        Check rate limit for FastAPI request

        Args:
            request: FastAPI request

        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        # Use API key as identifier if present, otherwise IP
        api_key = request.headers.get("x-api-key")
        identifier = api_key if api_key else request.client.host

        if not self.check(identifier):
            retry_after = self.get_retry_after(identifier)
            logger.warning(f"Rate limit exceeded for {identifier}")
            raise RateLimitExceeded(retry_after)

    def reset(self, identifier: str | None = None) -> None:
        """Reset rate limit for identifier or all"""
        if identifier:
            if identifier in self._buckets:
                del self._buckets[identifier]
        else:
            self._buckets.clear()

    def get_stats(self, identifier: str) -> dict:
        """Get rate limit stats for identifier"""
        bucket = self._buckets.get(identifier, [])
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        bucket = [t for t in bucket if t > window_start]

        return {
            "identifier": identifier,
            "current_requests": len(bucket),
            "limit": self.rate,
            "remaining": max(0, self.rate - len(bucket)),
            "reset_in_seconds": self.get_retry_after(identifier) if bucket else 0,
        }


def rate_limit(
    requests_per_minute: int = 60, identifier_fn: Callable[[Request], str] | None = None
):
    """
    Decorator for rate limiting endpoints

    Example:
        @app.get("/api/endpoint")
        @rate_limit(requests_per_minute=10)
        async def endpoint(request: Request):
            ...
    """
    limiter = RateLimiter(requests_per_minute)

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request | None = None, **kwargs):
            if request:
                # Get identifier
                if identifier_fn:
                    identifier = identifier_fn(request)
                else:
                    # Use API key or IP
                    api_key = request.headers.get("x-api-key")
                    identifier = api_key if api_key else request.client.host

                # Check rate limit
                if not limiter.check(identifier):
                    retry_after = limiter.get_retry_after(identifier)
                    raise RateLimitExceeded(retry_after)

            return await func(*args, request=request, **kwargs)

        return wrapper

    return decorator


# Global rate limiters for different endpoints
_global_limiter = RateLimiter(requests_per_minute=100)  # Global default
_chat_limiter = RateLimiter(requests_per_minute=20)  # Chat endpoints
_admin_limiter = RateLimiter(requests_per_minute=30)  # Admin endpoints


def get_global_limiter() -> RateLimiter:
    """Get global rate limiter"""
    return _global_limiter


def get_chat_limiter() -> RateLimiter:
    """Get chat rate limiter"""
    return _chat_limiter


def get_admin_limiter() -> RateLimiter:
    """Get admin rate limiter"""
    return _admin_limiter
