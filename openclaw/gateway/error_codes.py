from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    NOT_LINKED = "NOT_LINKED"
    NOT_PAIRED = "NOT_PAIRED"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAVAILABLE = "UNAVAILABLE"


class GatewayError(Exception):
    def __init__(self, message: str, error_code: ErrorCode, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error_code.value,
            "message": str(self),
            "details": self.details,
        }


class NotLinkedError(GatewayError):
    def __init__(self, message: str | None = None):
        msg = message or "Not linked"
        super().__init__(msg, ErrorCode.NOT_LINKED)


class NotPairedError(GatewayError):
    def __init__(self, message: str | None = None):
        msg = message or "Not paired"
        super().__init__(msg, ErrorCode.NOT_PAIRED)


class AgentTimeoutError(GatewayError):
    def __init__(self, message: str | None = None):
        msg = message or "Agent timed out"
        super().__init__(msg, ErrorCode.AGENT_TIMEOUT)


class InvalidRequestError(GatewayError):
    def __init__(self, message: str | None = None):
        msg = message or "Invalid request"
        super().__init__(msg, ErrorCode.INVALID_REQUEST)


class UnavailableError(GatewayError):
    def __init__(self, message: str | None = None):
        msg = message or "Service unavailable"
        super().__init__(msg, ErrorCode.UNAVAILABLE)


__all__ = [
    "ErrorCode",
    "GatewayError",
    "NotLinkedError",
    "NotPairedError",
    "AgentTimeoutError",
    "InvalidRequestError",
    "UnavailableError",
]
