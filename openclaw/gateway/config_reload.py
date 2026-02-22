"""Config hot reload system.

Matches TypeScript openclaw/src/gateway/config-reload.ts:

Reload modes
-----------
- "off"     : Never reload; ignore file changes
- "restart" : Send SIGUSR1 to self to trigger full restart
- "hot"     : Update running state in-process without restart
- "hybrid"  : Hot-reload safe subsystems; restart for others

Path-based reload rules
-----------------------
Specific config paths can be mapped to "hot" or "restart" regardless of the
global mode.  Rules are evaluated in declaration order; first match wins.

Examples::

    reloader = ConfigReloader(
        config_path=Path("~/.openclaw/config.json"),
        on_hot_reload=async_callback,
        mode="hybrid",
        path_rules=[
            ("channels", "hot"),
            ("cron", "hot"),
            ("agents.skills", "restart"),
        ],
    )
    await reloader.start()
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import time
from pathlib import Path
from typing import Callable, Literal, Optional

from openclaw.config.loader import load_config, invalidate_config_cache

logger = logging.getLogger(__name__)

ReloadMode = Literal["off", "restart", "hot", "hybrid"]

# Subsystems that are hot-reloadable (matches TS config-reload.ts hotSubsystems)
_HOT_SUBSYSTEMS = {"channels", "cron", "hooks", "skills"}


class ConfigReloader:
    """Config file watcher and hot reloader.

    Replaces the old polling-based watcher with an event-driven watchdog observer.
    Supports reload modes and per-path rules.
    """

    def __init__(
        self,
        config_path: Path,
        on_hot_reload: Callable | None = None,
        mode: ReloadMode = "hybrid",
        path_rules: list[tuple[str, ReloadMode]] | None = None,
        debounce_ms: int = 500,
    ) -> None:
        self.config_path = Path(config_path).expanduser().resolve()
        self.on_hot_reload = on_hot_reload
        self.mode = mode
        self.path_rules: list[tuple[str, ReloadMode]] = path_rules or []
        self.debounce_ms = debounce_ms
        self._observer = None
        self._debounce_task: Optional[asyncio.Task] = None
        self._last_mtime: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start watching the config file for changes."""
        if self.mode == "off":
            logger.info("Config reloader is disabled (mode=off)")
            return

        logger.info(f"Starting config reloader: path={self.config_path} mode={self.mode}")
        self._last_mtime = self._get_mtime()
        self._start_watchdog()

    async def stop(self) -> None:
        """Stop watching."""
        if self._observer:
            try:
                self._observer.stop()
                self._observer.join(timeout=3)
            except Exception:
                pass
            self._observer = None
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        logger.info("Config reloader stopped")

    async def force_reload(self) -> None:
        """Manually trigger a reload cycle."""
        await self._handle_change()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_mtime(self) -> float:
        try:
            return self.config_path.stat().st_mtime
        except FileNotFoundError:
            return 0.0

    def _start_watchdog(self) -> None:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileSystemEvent

            reloader = self

            class _Handler(FileSystemEventHandler):
                def on_modified(self, event: FileSystemEvent) -> None:
                    if Path(event.src_path).resolve() == reloader.config_path:
                        reloader._schedule_debounced()

                def on_created(self, event: FileSystemEvent) -> None:
                    self.on_modified(event)

            handler = _Handler()
            observer = Observer()
            observer.schedule(handler, str(self.config_path.parent), recursive=False)
            observer.daemon = True
            observer.start()
            self._observer = observer
        except ImportError:
            # watchdog not installed – fall back to asyncio polling task
            logger.debug("watchdog not available; using asyncio polling")
            self._debounce_task = asyncio.create_task(self._polling_loop())

    def _schedule_debounced(self) -> None:
        """Schedule a debounced reload (called from watchdog thread)."""
        try:
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(self._enqueue_reload)
        except RuntimeError:
            pass

    def _enqueue_reload(self) -> None:
        """Enqueue reload, cancelling any existing debounce timer."""
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
        self._debounce_task = asyncio.create_task(self._debounced_reload())

    async def _debounced_reload(self) -> None:
        await asyncio.sleep(self.debounce_ms / 1000.0)
        await self._handle_change()

    async def _polling_loop(self) -> None:
        """Fallback polling loop when watchdog is unavailable."""
        while True:
            await asyncio.sleep(2)
            mtime = self._get_mtime()
            if mtime != self._last_mtime:
                self._last_mtime = mtime
                await self._handle_change()

    async def _handle_change(self) -> None:
        """Determine action and execute it."""
        logger.info(f"Config changed: {self.config_path}")
        self._last_mtime = self._get_mtime()

        # Invalidate in-process cache so next load_config() re-reads disk
        invalidate_config_cache()

        action = self._resolve_action()
        logger.info(f"Config reload action: {action}")

        if action == "off":
            return
        if action == "restart":
            await self._do_restart()
        else:
            await self._do_hot_reload()

    def _resolve_action(self) -> ReloadMode:
        """
        Determine the reload action for the current change.

        Path rules are checked first; they can override the global mode for
        specific config sub-keys.  The logic mirrors TS buildReloadPlan().
        """
        if self.mode == "off":
            return "off"

        # Load new config to peek at changed keys
        try:
            new_cfg = load_config()
            changed_keys = _top_level_keys(new_cfg)
        except Exception:
            changed_keys = []

        # Path-rule matching
        for prefix, rule_mode in self.path_rules:
            for key in changed_keys:
                if key == prefix or key.startswith(f"{prefix}."):
                    logger.debug(f"Path rule matched: {prefix!r} → {rule_mode}")
                    return rule_mode

        if self.mode == "hot":
            return "hot"
        if self.mode == "restart":
            return "restart"

        # hybrid: hot if only hot-reloadable subsystems changed
        if self.mode == "hybrid":
            if changed_keys and all(k in _HOT_SUBSYSTEMS for k in changed_keys):
                return "hot"
            return "restart"

        return "hot"

    async def _do_hot_reload(self) -> None:
        """Apply hot reload – call on_hot_reload callback."""
        logger.info("Hot-reloading config…")
        try:
            new_config = load_config()
            if self.on_hot_reload:
                await self.on_hot_reload(new_config)
            logger.info("Config hot-reloaded successfully")
        except Exception as exc:
            logger.error(f"Hot-reload failed: {exc}")

    async def _do_restart(self) -> None:
        """Send SIGUSR1 to self, which the process should handle to restart."""
        logger.info("Config change requires restart – sending SIGUSR1")
        try:
            os.kill(os.getpid(), signal.SIGUSR1)
        except (OSError, AttributeError):
            # Windows doesn't have SIGUSR1; just do a hot reload as best-effort
            logger.warning("SIGUSR1 not available – falling back to hot reload")
            await self._do_hot_reload()


def _top_level_keys(config: object) -> list[str]:
    """Extract top-level dict keys from a config object."""
    if isinstance(config, dict):
        return list(config.keys())
    if hasattr(config, "model_fields"):
        return list(config.model_fields.keys())
    if hasattr(config, "__dict__"):
        return list(config.__dict__.keys())
    return []


async def start_config_reloader(
    config_path: Path,
    on_reload: Callable | None = None,
    mode: ReloadMode = "hybrid",
    path_rules: list[tuple[str, ReloadMode]] | None = None,
) -> "ConfigReloader":
    """Start config file reloader and return the instance.

    Args:
        config_path: Path to config file.
        on_reload: Async callback(new_config) for hot reloads.
        mode: Global reload mode ("off"|"restart"|"hot"|"hybrid").
        path_rules: Per-path overrides – list of (key_prefix, mode).

    Returns:
        Running ConfigReloader instance.
    """
    reloader = ConfigReloader(
        config_path=config_path,
        on_hot_reload=on_reload,
        mode=mode,
        path_rules=path_rules,
    )
    await reloader.start()
    return reloader


__all__ = ["ConfigReloader", "ConfigReloader", "start_config_reloader", "ReloadMode"]
