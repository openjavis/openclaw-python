"""
Authentication middleware for FastAPI
"""

import logging
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .api_keys import get_api_key_manager
from .rate_limiter import get_global_limiter

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware

    Validates API keys and enforces rate limits
    """

    def __init__(
        self,
        app: ASGIApp,
        skip_auth_paths: list[str] | None = None,
        enable_rate_limiting: bool = True,
    ):
        super().__init__(app)
        self.skip_auth_paths = skip_auth_paths or [
            "/",
            "/health",
            "/health/live",
            "/health/ready",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        self.enable_rate_limiting = enable_rate_limiting
        self.api_key_manager = get_api_key_manager()
        self.rate_limiter = get_global_limiter()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through middleware"""
        # Skip auth for public paths
        if request.url.path in self.skip_auth_paths:
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("x-api-key")
        if api_key:
            validated_key = self.api_key_manager.validate_key(api_key)
            if validated_key:
                # Attach to request state
                request.state.api_key = validated_key
            else:
                logger.warning(f"Invalid API key from {request.client.host}")
                return Response(
                    content='{"detail": "Invalid or expired API key"}',
                    status_code=401,
                    media_type="application/json",
                )

        # Rate limiting
        if self.enable_rate_limiting:
            identifier = api_key if api_key else request.client.host
            if not self.rate_limiter.check(identifier):
                retry_after = self.rate_limiter.get_retry_after(identifier)
                logger.warning(f"Rate limit exceeded for {identifier}")
                return Response(
                    content=f'{{"detail": "Rate limit exceeded. Try again in {retry_after}s"}}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(retry_after)},
                )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        if api_key:
            stats = self.rate_limiter.get_stats(api_key)
            response.headers["X-RateLimit-Limit"] = str(stats["limit"])
            response.headers["X-RateLimit-Remaining"] = str(stats["remaining"])
            response.headers["X-RateLimit-Reset"] = str(stats["reset_in_seconds"])

        return response


def setup_auth_middleware(
    app, skip_auth_paths: list[str] | None = None, enable_rate_limiting: bool = True
) -> None:
    """
    Setup authentication middleware for FastAPI app

    Args:
        app: FastAPI application
        skip_auth_paths: Paths to skip authentication
        enable_rate_limiting: Enable rate limiting
    """
    app.add_middleware(
        AuthMiddleware, skip_auth_paths=skip_auth_paths, enable_rate_limiting=enable_rate_limiting
    )
    logger.info("Auth middleware configured")
