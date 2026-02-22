"""Abort signal implementation for cancellable operations

Matches JavaScript AbortController/AbortSignal pattern.
"""
from __future__ import annotations
import asyncio
from typing import Callable


class AbortError(Exception):
    """Raised when operation is aborted"""
    pass


class AbortSignal:
    """
    Signal for cancellable operations
    
    Matches JavaScript AbortSignal API.
    """
    
    def __init__(self):
        self._aborted = False
        self._callbacks: list[Callable[[], None]] = []
        self._reason: Exception | None = None
    
    @property
    def aborted(self) -> bool:
        """Check if signal is aborted"""
        return self._aborted
    
    @property
    def reason(self) -> Exception | None:
        """Get abort reason"""
        return self._reason
    
    def throw_if_aborted(self) -> None:
        """Throw AbortError if aborted"""
        if self._aborted:
            raise self._reason or AbortError("Operation aborted")
    
    def add_listener(self, callback: Callable[[], None]) -> None:
        """Add abort listener"""
        if self._aborted:
            callback()
        else:
            self._callbacks.append(callback)
    
    def remove_listener(self, callback: Callable[[], None]) -> None:
        """Remove abort listener"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def abort(self, reason: Exception | None = None) -> None:
        """Abort the signal (public method, matches AbortController.abort() API)"""
        self._trigger_abort(reason)

    def _trigger_abort(self, reason: Exception | None = None) -> None:
        """Internal method to trigger abort"""
        if self._aborted:
            return
        
        self._aborted = True
        self._reason = reason or AbortError("Operation aborted")
        
        # Call all listeners
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass  # Ignore errors in callbacks
        
        self._callbacks.clear()


class AbortController:
    """
    Controller for AbortSignal
    
    Matches JavaScript AbortController API.
    """
    
    def __init__(self):
        self._signal = AbortSignal()
    
    @property
    def signal(self) -> AbortSignal:
        """Get the associated signal"""
        return self._signal
    
    def abort(self, reason: Exception | None = None) -> None:
        """Abort the operation"""
        self._signal._trigger_abort(reason)


def create_timeout_signal(timeout_seconds: float) -> AbortSignal:
    """
    Create abort signal that triggers after timeout
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Returns:
        AbortSignal that will abort after timeout
    """
    controller = AbortController()
    
    async def timeout_task():
        await asyncio.sleep(timeout_seconds)
        controller.abort(TimeoutError(f"Operation timed out after {timeout_seconds}s"))
    
    asyncio.create_task(timeout_task())
    
    return controller.signal


def combine_signals(*signals: AbortSignal) -> AbortSignal:
    """
    Combine multiple abort signals
    
    Returns signal that aborts when any input signal aborts.
    
    Args:
        *signals: Signals to combine
        
    Returns:
        Combined abort signal
    """
    controller = AbortController()
    
    def on_abort():
        controller.abort()
    
    for signal in signals:
        signal.add_listener(on_abort)
    
    return controller.signal
