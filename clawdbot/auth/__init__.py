"""
Authentication and authorization module
"""
from .api_keys import (
    APIKeyManager,
    APIKey,
    verify_api_key,
    get_api_key_manager
)
from .rate_limiter import (
    RateLimiter,
    RateLimitExceeded,
    rate_limit
)
from .middleware import (
    AuthMiddleware,
    setup_auth_middleware
)

__all__ = [
    "APIKeyManager",
    "APIKey",
    "verify_api_key",
    "get_api_key_manager",
    "RateLimiter",
    "RateLimitExceeded",
    "rate_limit",
    "AuthMiddleware",
    "setup_auth_middleware",
]
