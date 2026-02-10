"""Job store matching TypeScript openclaw/src/cron/service/store.ts"""
from __future__ import annotations

import json
import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .types import CronJob

logger = logging.getLogger(__name__)


class CronStore:
    """
    File-based persistent storage for cron jobs
    
    Features:
    - JSON5 format with comments
    - Atomic writes (temp file + rename)
    - Automatic backups
    """
    
    def __init__(self, store_path: Path):
        """
        Initialize cron store
        
        Args:
            store_path: Path to jobs.json file
        """
        self.store_path = store_path
        self.backup_path = store_path.with_suffix(".json.bak")
        
        # Ensure parent directory exists
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> list[CronJob]:
        """
        Load jobs from store
        
        Returns:
            List of cron jobs
        """
        if not self.store_path.exists():
            logger.info(f"Store file not found: {self.store_path}")
            return []
        
        try:
            with open(self.store_path) as f:
                data = json.load(f)
            
            # Parse jobs
            jobs_data = data.get("jobs", [])
            jobs = []
            
            for job_data in jobs_data:
                try:
                    job = CronJob.from_dict(job_data)
                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing job: {e}", exc_info=True)
                    continue
            
            logger.info(f"Loaded {len(jobs)} jobs from {self.store_path}")
            return jobs
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing store file: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading store: {e}", exc_info=True)
            return []
    
    def save(self, jobs: list[CronJob]) -> None:
        """
        Save jobs to store
        
        Args:
            jobs: List of cron jobs to save
        """
        try:
            # Create backup if store exists
            if self.store_path.exists():
                shutil.copy2(self.store_path, self.backup_path)
                logger.debug(f"Created backup: {self.backup_path}")
            
            # Convert jobs to dictionaries
            jobs_data = [job.to_dict() for job in jobs]
            
            # Prepare data
            data = {
                "version": 1,
                "jobs": jobs_data
            }
            
            # Write to temp file first (atomic write)
            temp_path = self.store_path.with_suffix(f".tmp.{uuid.uuid4().hex[:8]}")
            
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
            
            # Rename to final path (atomic on most filesystems)
            temp_path.replace(self.store_path)
            
            logger.info(f"Saved {len(jobs)} jobs to {self.store_path}")
            
        except Exception as e:
            logger.error(f"Error saving store: {e}", exc_info=True)
            # Clean up temp file if it exists
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            raise
    
    def migrate_if_needed(self) -> None:
        """Migrate store format if needed"""
        if not self.store_path.exists():
            return
        
        try:
            with open(self.store_path) as f:
                data = json.load(f)
            
            version = data.get("version", 0)
            
            if version == 0:
                # Migrate from v0 to v1
                logger.info("Migrating store from v0 to v1")
                
                # v0 format: list of jobs directly
                # v1 format: {"version": 1, "jobs": [...]}
                if isinstance(data, list):
                    migrated_data = {
                        "version": 1,
                        "jobs": data
                    }
                    
                    # Save migrated data
                    with open(self.store_path, "w") as f:
                        json.dump(migrated_data, f, indent=2)
                    
                    logger.info("Migration complete")
            
        except Exception as e:
            logger.error(f"Error migrating store: {e}", exc_info=True)


class CronRunLog:
    """
    Run log for cron job execution history
    
    Features:
    - JSONL format (one line per run)
    - Auto-pruning (keep recent runs)
    """
    
    def __init__(self, log_dir: Path, job_id: str, max_entries: int = 100):
        """
        Initialize run log
        
        Args:
            log_dir: Directory for run logs
            job_id: Job ID
            max_entries: Maximum entries to keep
        """
        self.log_path = log_dir / f"{job_id}.jsonl"
        self.max_entries = max_entries
        
        # Ensure log directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def append(self, entry: dict[str, Any]) -> None:
        """
        Append run entry to log
        
        Args:
            entry: Run entry data
        """
        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            
            # Prune if needed
            self._prune_if_needed()
            
        except Exception as e:
            logger.error(f"Error appending to run log: {e}", exc_info=True)
    
    def read(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Read run log entries
        
        Args:
            limit: Maximum entries to return (most recent)
            
        Returns:
            List of run entries
        """
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
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing log entry: {e}")
                        continue
            
            # Return most recent entries if limit specified
            if limit:
                return entries[-limit:]
            
            return entries
            
        except Exception as e:
            logger.error(f"Error reading run log: {e}", exc_info=True)
            return []
    
    def _prune_if_needed(self) -> None:
        """Prune old entries if log exceeds max_entries"""
        entries = self.read()
        
        if len(entries) > self.max_entries:
            # Keep only most recent entries
            entries = entries[-self.max_entries:]
            
            # Rewrite log file
            try:
                with open(self.log_path, "w") as f:
                    for entry in entries:
                        f.write(json.dumps(entry) + "\n")
                
                logger.debug(f"Pruned run log to {len(entries)} entries")
                
            except Exception as e:
                logger.error(f"Error pruning run log: {e}", exc_info=True)
    
    def clear(self) -> None:
        """Clear run log"""
        try:
            if self.log_path.exists():
                self.log_path.unlink()
            logger.info(f"Cleared run log: {self.log_path}")
        except Exception as e:
            logger.error(f"Error clearing run log: {e}", exc_info=True)
