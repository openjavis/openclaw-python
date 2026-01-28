"""
Model failover chain management
"""

from .chain import FallbackChain, FallbackManager
from .errors import FailoverReason, FallbackError

__all__ = ["FallbackChain", "FallbackManager", "FallbackError", "FailoverReason"]
