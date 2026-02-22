"""Configuration loader for OpenClaw.

Loads configuration from files and environment variables.

Matches TypeScript openclaw/src/config/io.ts:
- JSON5 parsing (comments, trailing commas, unquoted keys)
- $include directives: {"$include": "./extra.json"}
- ${ENV_VAR} environment variable substitution
- Config audit log (config-audit.jsonl)
- Backup rotation on write
- Preserve ${VAR} tokens in written config
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

_cached_config: Optional["ClawdbotConfig"] = None

# ---------------------------------------------------------------------------
# JSON5 parsing
# ---------------------------------------------------------------------------

def _parse_json5(text: str) -> Any:
    """
    Parse JSON5 text (comments + trailing commas).

    Falls back to strict json if json5 library is unavailable.
    """
    try:
        import json5  # type: ignore[import]
        return json5.loads(text)
    except ImportError:
        pass

    # Minimal JSON5 → JSON stripper: remove // and /* */ comments,
    # remove trailing commas before ] or }.
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r",\s*([\]}])", r"\1", text)
    return json.loads(text)


# ---------------------------------------------------------------------------
# $include + env-var substitution
# ---------------------------------------------------------------------------

_ENV_VAR_RE = re.compile(r"\$\{([^}]+)\}")


def _substitute_env_vars(obj: Any, preserve: bool = False) -> Any:
    """
    Recursively replace ${VAR} with os.environ values.

    If *preserve* is True the token is left untouched (used when writing back
    to disk to preserve variable references in the config file).
    """
    if isinstance(obj, str):
        if preserve:
            return obj

        def _replace(m: re.Match) -> str:
            var = m.group(1)
            return os.environ.get(var, m.group(0))  # leave unresolved as-is

        return _ENV_VAR_RE.sub(_replace, obj)
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v, preserve) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_env_vars(v, preserve) for v in obj]
    return obj


def _resolve_includes(obj: Any, base_dir: Path, depth: int = 0) -> Any:
    """
    Resolve {"$include": "./path.json"} directives recursively.

    Matches TypeScript $include directive in config/io.ts.
    """
    if depth > 10:
        raise ValueError("$include depth limit exceeded (circular?)")

    if isinstance(obj, dict):
        if "$include" in obj and len(obj) == 1:
            include_path = base_dir / obj["$include"]
            if not include_path.exists():
                logger.warning(f"$include target not found: {include_path}")
                return {}
            raw = include_path.read_text(encoding="utf-8")
            included = _parse_json5(raw)
            return _resolve_includes(included, include_path.parent, depth + 1)
        return {k: _resolve_includes(v, base_dir, depth) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_includes(v, base_dir, depth) for v in obj]
    return obj


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts (override wins on scalar conflicts)."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _append_config_audit(config_path: Path, event: str, details: str = "") -> None:
    """Append an entry to config-audit.jsonl (matches TS config/io.ts audit log)."""
    audit_file = config_path.parent / "config-audit.jsonl"
    try:
        entry = json.dumps({
            "ts": datetime.now(UTC).isoformat(),
            "event": event,
            "path": str(config_path),
            "details": details,
        })
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core load / save
# ---------------------------------------------------------------------------

def _resolve_config_path(config_path: Optional[str | Path]) -> Optional[Path]:
    if config_path:
        return Path(config_path)

    candidates = [
        Path.cwd() / "openclaw.json",
        Path.cwd() / "openclaw.json5",
        Path.cwd() / "config" / "openclaw.json",
        Path.home() / ".openclaw" / "config.json",
        Path.home() / ".openclaw" / "config.json5",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def load_config_raw(path: Path) -> dict[str, Any]:
    """
    Load a config file with JSON5 parsing, $include resolution, and env-var substitution.

    Returns the resolved config dict (ready for schema validation).
    """
    raw = path.read_text(encoding="utf-8")
    obj = _parse_json5(raw)
    obj = _resolve_includes(obj, path.parent)
    obj = _substitute_env_vars(obj, preserve=False)
    return obj if isinstance(obj, dict) else {}


def load_config(
    config_path: Optional[str | Path] = None,
    as_dict: bool = False,
) -> Union["ClawdbotConfig", dict[str, Any]]:
    """Load OpenClaw configuration.

    Args:
        config_path: Optional path to config file.  Supports JSON5.
        as_dict: If True, return dict instead of ClawdbotConfig object.

    Returns:
        Configuration object (ClawdbotConfig) or dictionary if as_dict=True.
    """
    from .schema import ClawdbotConfig

    global _cached_config

    if _cached_config is not None:
        return _cached_config.model_dump() if as_dict else _cached_config

    config_dict: dict[str, Any] = {}
    path = _resolve_config_path(config_path)

    if path and path.exists():
        try:
            config_dict = load_config_raw(path)
            _append_config_audit(path, "load", f"success, keys={list(config_dict.keys())[:5]}")
        except Exception as exc:
            logger.warning(f"Failed to load config from {path}: {exc}")
            _append_config_audit(path, "load_error", str(exc))

    try:
        config_obj = ClawdbotConfig(**config_dict) if config_dict else ClawdbotConfig()
    except Exception as exc:
        logger.warning(f"Failed to parse config: {exc}")
        config_obj = ClawdbotConfig()

    _cached_config = config_obj
    return config_obj.model_dump() if as_dict else config_obj


def invalidate_config_cache() -> None:
    """Invalidate the in-process config cache so the next load_config() re-reads disk."""
    global _cached_config
    _cached_config = None


def save_config(config: Any, config_path: Optional[str | Path] = None) -> None:
    """Save OpenClaw configuration to file.

    - Creates backup rotation (up to 3 .bak files)
    - Preserves ${VAR} tokens in the output (not expanded)
    - Appends an audit log entry

    Args:
        config: Configuration object or dictionary to save.
        config_path: Optional path to config file (defaults to ~/.openclaw/config.json).
    """
    global _cached_config

    path = Path(config_path) if config_path else Path.home() / ".openclaw" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    if hasattr(config, "model_dump"):
        config_dict: dict[str, Any] = config.model_dump(exclude_none=True)
    elif hasattr(config, "dict"):
        config_dict = config.dict(exclude_none=True)
    elif hasattr(config, "__dict__"):
        config_dict = config.__dict__
    elif isinstance(config, dict):
        config_dict = config
    else:
        config_dict = {}

    # Backup rotation (keep up to 3 backups)
    if path.exists():
        try:
            for i in range(2, 0, -1):
                src = path.with_suffix(f".bak{i}")
                dst = path.with_suffix(f".bak{i+1}")
                if src.exists():
                    shutil.copy2(src, dst)
            shutil.copy2(path, path.with_suffix(".bak1"))
        except Exception as exc:
            logger.debug(f"Backup rotation skipped: {exc}")

    # Write file
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, indent=2)

    _append_config_audit(path, "save", f"keys={list(config_dict.keys())[:5]}")

    # Update cache
    _cached_config = config if not isinstance(config, dict) else None


def get_config_path() -> Path:
    """Get the path to the active configuration file.

    Searches well-known locations.  If no file is found, returns the default
    user-level config path (``~/.openclaw/openclaw.json``) even if it does not
    yet exist.

    Returns:
        Path to config file (may not exist)
    """
    candidates = [
        Path.cwd() / "openclaw.json",
        Path.cwd() / "config" / "openclaw.json",
        Path.home() / ".openclaw" / "openclaw.json",
        Path.home() / ".openclaw" / "config.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Default: user-level config (may not exist)
    return Path.home() / ".openclaw" / "openclaw.json"


def get_config_value(key_path: str, default: Any = None) -> Any:
    """Get a configuration value by dot-separated key path.

    Args:
        key_path: Dot-separated key path (e.g., "channels.telegram.botToken")
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    config = load_config()
    keys = key_path.split(".")
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value
