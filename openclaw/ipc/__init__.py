"""Inter-process communication"""

from .message_queue import MessageQueue, MessageQueueBackend

__all__ = ["MessageQueue", "MessageQueueBackend"]
