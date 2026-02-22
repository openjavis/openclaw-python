"""Session write lock

File-based lock tied to session file path to serialize concurrent writes.
Matches TypeScript acquireSessionWriteLock() in openclaw/src/agents/session-lock.ts.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_MAX_HOLD_MS = 60_000  # 1 minute


class SessionWriteLockError(Exception):
    """Raised when a session write lock cannot be acquired in time."""


class SessionWriteLock:
    """
    File-based async write lock for a session JSONL file.

    Usage::

        lock = SessionWriteLock(session_file)
        async with lock.acquire(max_hold_ms=30_000):
            # safe to write
            ...

    If the lock is already held and ``max_hold_ms`` is exceeded the context
    manager raises ``SessionWriteLockError``.
    """

    def __init__(self, session_file: str | Path) -> None:
        self._session_file = Path(session_file)
        self._lock_file = self._session_file.with_suffix(".lock")
        self._asyncio_lock = asyncio.Lock()

    @property
    def lock_file(self) -> Path:
        return self._lock_file

    async def acquire(self, max_hold_ms: int = _DEFAULT_MAX_HOLD_MS) -> "SessionWriteLock":
        """Async context manager – acquire then release."""
        return self

    async def __aenter__(self) -> "SessionWriteLock":
        return self

    async def __aexit__(self, *_: object) -> None:
        self._release()

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    async def _acquire_inner(self, max_hold_ms: int) -> None:
        """Spin-wait until we can write the lock file or timeout."""
        deadline = time.monotonic() + max_hold_ms / 1000.0
        while True:
            if self._try_lock():
                return
            if time.monotonic() >= deadline:
                raise SessionWriteLockError(
                    f"Could not acquire session write lock for {self._session_file} "
                    f"within {max_hold_ms}ms"
                )
            await asyncio.sleep(0.05)

    def _try_lock(self) -> bool:
        """Try to atomically create the lock file (O_EXCL)."""
        try:
            self._lock_file.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(self._lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            # Check for stale lock (older than 5 minutes)
            try:
                mtime = self._lock_file.stat().st_mtime
                if time.time() - mtime > 300:
                    logger.warning(f"Removing stale lock file: {self._lock_file}")
                    self._lock_file.unlink(missing_ok=True)
                    return self._try_lock()
            except Exception:
                pass
            return False
        except Exception as exc:
            logger.debug(f"Lock attempt failed: {exc}")
            return False

    def _release(self) -> None:
        try:
            self._lock_file.unlink(missing_ok=True)
        except Exception as exc:
            logger.debug(f"Failed to release lock: {exc}")


class AcquireContext:
    """Returned by SessionWriteLock.acquire() for use as async ctx manager."""

    def __init__(self, lock: "SessionWriteLock", max_hold_ms: int) -> None:
        self._lock = lock
        self._max_hold_ms = max_hold_ms

    async def __aenter__(self) -> "SessionWriteLock":
        await self._lock._acquire_inner(self._max_hold_ms)
        return self._lock

    async def __aexit__(self, *_: object) -> None:
        self._lock._release()


def acquire_session_write_lock(
    session_file: str | Path,
    max_hold_ms: int = _DEFAULT_MAX_HOLD_MS,
) -> "AcquireContext":
    """
    Acquire a write lock for the given session file.

    Matches TypeScript::

        const release = await acquireSessionWriteLock({ sessionFile, maxHoldMs });
        try { ... } finally { release(); }

    Usage::

        async with acquire_session_write_lock(session_file, max_hold_ms=30_000):
            ...
    """
    lock = SessionWriteLock(session_file)
    return AcquireContext(lock, max_hold_ms)
