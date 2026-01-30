"""Gateway protocol schemas and types"""

from .frames import ErrorShape, EventFrame, RequestFrame, ResponseFrame

__all__ = ["RequestFrame", "ResponseFrame", "EventFrame", "ErrorShape"]
