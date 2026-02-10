"""Message queue for inter-process communication

Provides message queue abstraction with multiple backends.
"""
from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MessageQueueBackend(str, Enum):
    """Message queue backend types"""
    MEMORY = "memory"  # In-memory (for testing)
    REDIS = "redis"    # Redis pub/sub
    UNIX = "unix"      # Unix domain sockets


@dataclass
class Message:
    """IPC message"""
    
    type: str
    sender: str
    recipient: str
    payload: dict[str, Any]
    timestamp: float


class MessageQueue(ABC):
    """Abstract message queue"""
    
    @abstractmethod
    async def send(self, message: Message):
        """Send message"""
        pass
    
    @abstractmethod
    async def receive(self, timeout: float = 1.0) -> Message | None:
        """Receive message"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close queue"""
        pass


class MemoryMessageQueue(MessageQueue):
    """In-memory message queue (for testing/single process)"""
    
    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self._queue: asyncio.Queue = asyncio.Queue()
    
    async def send(self, message: Message):
        """Send message to queue"""
        await self._queue.put(message)
        logger.debug(f"Sent message: {message.type} to {message.recipient}")
    
    async def receive(self, timeout: float = 1.0) -> Message | None:
        """Receive message from queue"""
        try:
            message = await asyncio.wait_for(
                self._queue.get(),
                timeout=timeout
            )
            logger.debug(f"Received message: {message.type} from {message.sender}")
            return message
        except asyncio.TimeoutError:
            return None
    
    async def close(self):
        """Close queue"""
        # Clear queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break


class RedisMessageQueue(MessageQueue):
    """Redis-based message queue"""
    
    def __init__(self, queue_name: str, redis_url: str = "redis://localhost"):
        self.queue_name = queue_name
        self.redis_url = redis_url
        self._client = None
        self._pubsub = None
    
    async def _ensure_connected(self):
        """Ensure Redis connection"""
        if self._client is None:
            try:
                import redis.asyncio as aioredis
                self._client = await aioredis.from_url(self.redis_url)
                self._pubsub = self._client.pubsub()
                await self._pubsub.subscribe(self.queue_name)
            except ImportError:
                raise RuntimeError("redis package not installed. Install with: pip install redis")
    
    async def send(self, message: Message):
        """Send message via Redis pub/sub"""
        await self._ensure_connected()
        
        # Serialize message
        data = json.dumps({
            "type": message.type,
            "sender": message.sender,
            "recipient": message.recipient,
            "payload": message.payload,
            "timestamp": message.timestamp,
        })
        
        # Publish to channel
        await self._client.publish(self.queue_name, data)
        logger.debug(f"Published message: {message.type}")
    
    async def receive(self, timeout: float = 1.0) -> Message | None:
        """Receive message from Redis"""
        await self._ensure_connected()
        
        try:
            # Get message with timeout
            async with asyncio.timeout(timeout):
                msg = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=timeout
                )
                
                if msg and msg["type"] == "message":
                    data = json.loads(msg["data"])
                    return Message(**data)
            
            return None
            
        except asyncio.TimeoutError:
            return None
    
    async def close(self):
        """Close Redis connection"""
        if self._pubsub:
            await self._pubsub.unsubscribe(self.queue_name)
            await self._pubsub.close()
        
        if self._client:
            await self._client.close()


def create_message_queue(
    backend: MessageQueueBackend,
    queue_name: str,
    **kwargs
) -> MessageQueue:
    """
    Create message queue with specified backend
    
    Args:
        backend: Backend type
        queue_name: Queue name
        **kwargs: Backend-specific options
        
    Returns:
        MessageQueue instance
    """
    if backend == MessageQueueBackend.MEMORY:
        return MemoryMessageQueue(queue_name)
    elif backend == MessageQueueBackend.REDIS:
        redis_url = kwargs.get("redis_url", "redis://localhost")
        return RedisMessageQueue(queue_name, redis_url)
    else:
        raise ValueError(f"Unsupported backend: {backend}")
