"""Job store matching TypeScript openclaw/src/cron/service/store.ts

Key features:
- JSON file with atomic writes
- mtime-based change detection for fast ensureLoaded
- Legacy field migration
- Backup before overwrite
- Run log (JSONL) per job
"""
from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import Any

from .types import CronJob

logger = logging.getLogger(__name__)


class CronStore:
    """
    File-based persistent storage for cron jobs.

    Provides:
    - Atomic writes (temp file + rename)
    - Automatic backups
    - mtime tracking for cache invalidation
    """

    def __init__(self, store_path: Path):
        self.store_path = store_path
        self.backup_path = store_path.with_suffix(".json.bak")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # mtime helpers
    # ------------------------------------------------------------------
    def get_file_mtime_ms(self) -> float | None:
        """Get file modification time in ms (None if missing)."""
        try:
            return self.store_path.stat().st_mtime_ns / 1e6
        except FileNotFoundError:
            return None

    # ------------------------------------------------------------------
    # load / save
    # ------------------------------------------------------------------
    def load(self) -> list[CronJob]:
        """Load jobs from store, applying migrations."""
        if not self.store_path.exists():
            logger.info(f"Store file not found: {self.store_path}")
            return []

        try:
            with open(self.store_path) as f:
                data = json.load(f)

            # Handle v0 format (bare list)
            if isinstance(data, list):
                jobs_data = data
                mutated = True
            else:
                jobs_data = data.get("jobs", [])
                mutated = False

            jobs: list[CronJob] = []

            for raw in jobs_data:
                try:
                    # --- Legacy migrations (matches TypeScript ensureLoaded) ---
                    if self._migrate_job_fields(raw):
                        mutated = True

                    job = CronJob.from_dict(raw)
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing job: {e}", exc_info=True)
                    continue

            if mutated:
                # Re-save with migrations applied
                self.save(jobs)

            logger.info(f"Loaded {len(jobs)} jobs from {self.store_path}")
            return jobs

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing store file: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading store: {e}", exc_info=True)
            return []

    def save(self, jobs: list[CronJob]) -> None:
        """Save jobs to store (atomic write with backup)."""
        try:
            if self.store_path.exists():
                shutil.copy2(self.store_path, self.backup_path)

            jobs_data = [job.to_dict() for job in jobs]
            data = {"version": 1, "jobs": jobs_data}

            temp_path = self.store_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)

            temp_path.replace(self.store_path)
            logger.debug(f"Saved {len(jobs)} jobs to {self.store_path}")

        except Exception as e:
            logger.error(f"Error saving store: {e}", exc_info=True)
            if "temp_path" in locals() and temp_path.exists():
                temp_path.unlink()
            raise

    def migrate_if_needed(self) -> None:
        """Run migration on existing store file."""
        if not self.store_path.exists():
            return
        # Just loading triggers migrations
        self.load()

    # ------------------------------------------------------------------
    # Legacy migration (matches TypeScript ensureLoaded migration block)
    # ------------------------------------------------------------------
    @staticmethod
    def _migrate_job_fields(raw: dict[str, Any]) -> bool:
        """Migrate legacy fields on a single raw job dict. Returns True if mutated."""
        mutated = False

        # name: ensure non-empty trimmed string
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raw["name"] = _infer_legacy_name(raw)
            mutated = True
        else:
            trimmed = name.strip()
            if trimmed != name:
                raw["name"] = trimmed
                mutated = True

        # description: normalize optional text
        desc = raw.get("description")
        norm_desc = desc.strip() if isinstance(desc, str) and desc.strip() else None
        if raw.get("description") != norm_desc:
            raw["description"] = norm_desc
            mutated = True

        # enabled: must be bool
        if not isinstance(raw.get("enabled"), bool):
            raw["enabled"] = True
            mutated = True

        # payload migration (kind field)
        payload = raw.get("payload")
        if isinstance(payload, dict):
            kind = payload.get("kind", "")
            # Legacy: "message" used instead of "prompt"
            if kind == "agentTurn" and "message" in payload and "prompt" not in payload:
                payload["prompt"] = payload.pop("message")
                mutated = True

        # schedule migration
        schedule = raw.get("schedule")
        if isinstance(schedule, dict):
            kind = schedule.get("type", schedule.get("kind", ""))
            if not kind:
                if "at" in schedule or "atMs" in schedule or "timestamp" in schedule:
                    schedule["type"] = "at"
                    mutated = True
                elif "interval_ms" in schedule or "intervalMs" in schedule:
                    schedule["type"] = "every"
                    mutated = True
                elif "expression" in schedule:
                    schedule["type"] = "cron"
                    mutated = True
            # Normalize kind -> type
            if "kind" in schedule and "type" not in schedule:
                schedule["type"] = schedule.pop("kind")
                mutated = True

        # delivery mode: "deliver" -> "announce"
        delivery = raw.get("delivery")
        if isinstance(delivery, dict):
            mode = delivery.get("mode", "")
            if isinstance(mode, str) and mode.strip().lower() == "deliver":
                delivery["mode"] = "announce"
                mutated = True

        # Legacy isolation field: remove
        if "isolation" in raw:
            del raw["isolation"]
            mutated = True

        # Legacy delivery hints in payload
        if isinstance(payload, dict) and _has_legacy_delivery_hints(payload):
            if not isinstance(delivery, dict):
                raw["delivery"] = _build_delivery_from_legacy_payload(payload)
                mutated = True
            _strip_legacy_delivery_fields(payload)
            mutated = True

        return mutated


# ---------------------------------------------------------------------------
# Legacy helpers
# ---------------------------------------------------------------------------

def _infer_legacy_name(raw: dict[str, Any]) -> str:
    """Infer a name for a legacy job without one."""
    payload = raw.get("payload", {})
    if isinstance(payload, dict):
        kind = payload.get("kind", "")
        if kind == "systemEvent":
            text = payload.get("text", "")
            if text:
                return text[:40].strip()
        elif kind == "agentTurn":
            prompt = payload.get("prompt", payload.get("message", ""))
            if prompt:
                return prompt[:40].strip()
    schedule = raw.get("schedule", {})
    stype = schedule.get("type", "") if isinstance(schedule, dict) else ""
    return f"Cron job ({stype})" if stype else "Unnamed job"


def _has_legacy_delivery_hints(payload: dict[str, Any]) -> bool:
    if isinstance(payload.get("deliver"), bool):
        return True
    if isinstance(payload.get("bestEffortDeliver"), bool):
        return True
    to = payload.get("to")
    if isinstance(to, str) and to.strip():
        return True
    return False


def _build_delivery_from_legacy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    deliver = payload.get("deliver")
    mode = "none" if deliver is False else "announce"
    channel = payload.get("channel", "")
    to = payload.get("to", "")
    result: dict[str, Any] = {"mode": mode}
    if isinstance(channel, str) and channel.strip():
        result["channel"] = channel.strip().lower()
    if isinstance(to, str) and to.strip():
        result["to"] = to.strip()
    if isinstance(payload.get("bestEffortDeliver"), bool):
        result["bestEffort"] = payload["bestEffortDeliver"]
    return result


def _strip_legacy_delivery_fields(payload: dict[str, Any]) -> None:
    for key in ("deliver", "channel", "to", "bestEffortDeliver"):
        payload.pop(key, None)


# ---------------------------------------------------------------------------
# CronRunLog
# ---------------------------------------------------------------------------

class CronRunLog:
    """JSONL run log for cron job execution history."""

    def __init__(self, log_dir: Path, job_id: str, max_entries: int = 100):
        self.log_path = log_dir / f"{job_id}.jsonl"
        self.max_entries = max_entries
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: dict[str, Any]) -> None:
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            self._prune_if_needed()
        except Exception as e:
            logger.error(f"Error appending to run log: {e}", exc_info=True)

    def read(self, limit: int | None = None) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        try:
            entries: list[dict[str, Any]] = []
            with open(self.log_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            if limit:
                return entries[-limit:]
            return entries
        except Exception as e:
            logger.error(f"Error reading run log: {e}", exc_info=True)
            return []

    def _prune_if_needed(self) -> None:
        entries = self.read()
        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries:]
            try:
                with open(self.log_path, "w") as f:
                    for entry in entries:
                        f.write(json.dumps(entry) + "\n")
            except Exception as e:
                logger.error(f"Error pruning run log: {e}", exc_info=True)

    def clear(self) -> None:
        try:
            if self.log_path.exists():
                self.log_path.unlink()
        except Exception as e:
            logger.error(f"Error clearing run log: {e}", exc_info=True)
