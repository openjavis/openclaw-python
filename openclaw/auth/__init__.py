"""
Authentication and authorization module
"""

from .api_keys import APIKey, APIKeyManager, get_api_key_manager, verify_api_key
from .middleware import AuthMiddleware, setup_auth_middleware
from .rate_limiter import RateLimiter, RateLimitExceeded, rate_limit

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
