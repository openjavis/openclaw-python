"""Session tree structure matching pi-mono's SessionManager

This module implements tree-based session storage with:
- Append-only JSONL format
- Tree structure with parentId for branching
- Compaction summaries
- Branch summaries
- Label management
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class SessionEntry:
    """Base session entry"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    type: str = "message"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class MessageEntry(SessionEntry):
    """Message entry"""
    
    type: str = field(default="message", init=False)
    role: str = "user"
    content: str = ""
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompactionEntry(SessionEntry):
    """Compaction summary entry"""
    
    type: str = field(default="compaction", init=False)
    summary: str = ""
    removed_entries: list[str] = field(default_factory=list)
    tokens_before: int = 0
    tokens_after: int = 0


@dataclass
class BranchSummaryEntry(SessionEntry):
    """Branch summary entry"""
    
    type: str = field(default="branch_summary", init=False)
    summary: str = ""
    branch_id: str = ""


@dataclass
class ModelChangeEntry(SessionEntry):
    """Model change entry"""
    
    type: str = field(default="model_change", init=False)
    old_model: str = ""
    new_model: str = ""


@dataclass
class ThinkingLevelChangeEntry(SessionEntry):
    """Thinking level change entry"""
    
    type: str = field(default="thinking_level_change", init=False)
    old_level: str = ""
    new_level: str = ""


@dataclass
class CustomEntry(SessionEntry):
    """Custom entry (for extensions)"""
    
    type: str = "custom"
    custom_type: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class SessionTree:
    """
    Tree-based session storage with append-only JSONL format
    
    Features:
    - Append-only JSONL file format
    - Tree structure via parentId links
    - Branching support (fork, restore branch)
    - Compaction summaries
    - Label management
    """
    
    def __init__(self, session_path: Path):
        """
        Initialize session tree
        
        Args:
            session_path: Path to session JSONL file
        """
        self.session_path = session_path
        self.entries: list[SessionEntry] = []
        self.entry_map: dict[str, SessionEntry] = {}
        self.labels: dict[str, str] = {}  # label_name -> entry_id
        
        # Ensure session directory exists
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing session
        if self.session_path.exists():
            self._load()
    
    def _load(self) -> None:
        """Load session from JSONL file"""
        try:
            with open(self.session_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        entry = self._dict_to_entry(data)
                        self.entries.append(entry)
                        self.entry_map[entry.id] = entry
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing session entry: {e}")
                        continue
            
            logger.info(f"Loaded {len(self.entries)} entries from {self.session_path}")
            
        except Exception as e:
            logger.error(f"Error loading session: {e}", exc_info=True)
    
    def _dict_to_entry(self, data: dict[str, Any]) -> SessionEntry:
        """Convert dictionary to entry object"""
        entry_type = data.get("type", "message")
        
        if entry_type == "message":
            return MessageEntry(**{k: v for k, v in data.items() if k in MessageEntry.__annotations__})
        elif entry_type == "compaction":
            return CompactionEntry(**{k: v for k, v in data.items() if k in CompactionEntry.__annotations__})
        elif entry_type == "branch_summary":
            return BranchSummaryEntry(**{k: v for k, v in data.items() if k in BranchSummaryEntry.__annotations__})
        elif entry_type == "model_change":
            return ModelChangeEntry(**{k: v for k, v in data.items() if k in ModelChangeEntry.__annotations__})
        elif entry_type == "thinking_level_change":
            return ThinkingLevelChangeEntry(**{k: v for k, v in data.items() if k in ThinkingLevelChangeEntry.__annotations__})
        elif entry_type == "custom":
            return CustomEntry(**{k: v for k, v in data.items() if k in CustomEntry.__annotations__})
        else:
            # Unknown type, use SessionEntry base class
            return SessionEntry(**{k: v for k, v in data.items() if k in SessionEntry.__annotations__})
    
    def append(self, entry: SessionEntry) -> None:
        """
        Append entry to session
        
        Args:
            entry: Entry to append
        """
        # Add to memory
        self.entries.append(entry)
        self.entry_map[entry.id] = entry
        
        # Append to file
        try:
            with open(self.session_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Error appending to session: {e}", exc_info=True)
    
    def append_message(
        self,
        role: str,
        content: str,
        parent_id: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MessageEntry:
        """
        Append message entry
        
        Args:
            role: Message role (user, assistant, system, toolResult)
            content: Message content
            parent_id: Parent entry ID (for branching)
            tool_calls: Tool calls (for assistant messages)
            tool_call_id: Tool call ID (for tool results)
            metadata: Additional metadata
            
        Returns:
            Created message entry
        """
        entry = MessageEntry(
            parent_id=parent_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_call_id=tool_call_id,
            metadata=metadata or {}
        )
        
        self.append(entry)
        return entry
    
    def append_compaction(
        self,
        summary: str,
        removed_entries: list[str],
        tokens_before: int,
        tokens_after: int,
        parent_id: str | None = None,
    ) -> CompactionEntry:
        """
        Append compaction entry
        
        Args:
            summary: Compaction summary
            removed_entries: List of removed entry IDs
            tokens_before: Token count before compaction
            tokens_after: Token count after compaction
            parent_id: Parent entry ID
            
        Returns:
            Created compaction entry
        """
        entry = CompactionEntry(
            parent_id=parent_id,
            summary=summary,
            removed_entries=removed_entries,
            tokens_before=tokens_before,
            tokens_after=tokens_after
        )
        
        self.append(entry)
        return entry
    
    def get_branch(self, entry_id: str) -> list[SessionEntry]:
        """
        Get branch from root to entry
        
        Args:
            entry_id: Entry ID to trace back from
            
        Returns:
            List of entries from root to entry
        """
        branch: list[SessionEntry] = []
        current_id: str | None = entry_id
        
        while current_id:
            if current_id not in self.entry_map:
                logger.warning(f"Entry {current_id} not found in tree")
                break
            
            entry = self.entry_map[current_id]
            branch.insert(0, entry)
            current_id = entry.parent_id
        
        return branch
    
    def get_messages_in_branch(self, entry_id: str | None = None) -> list[MessageEntry]:
        """
        Get all messages in branch
        
        Args:
            entry_id: Entry ID (or None for latest)
            
        Returns:
            List of message entries
        """
        if entry_id is None:
            # Get latest entry
            if not self.entries:
                return []
            entry_id = self.entries[-1].id
        
        branch = self.get_branch(entry_id)
        return [e for e in branch if isinstance(e, MessageEntry)]
    
    def fork(self, from_entry_id: str, label: str | None = None) -> str:
        """
        Fork from entry
        
        Args:
            from_entry_id: Entry to fork from
            label: Optional label for the fork
            
        Returns:
            New branch entry ID
        """
        # Create a branch summary entry
        entry = BranchSummaryEntry(
            parent_id=from_entry_id,
            summary=f"Forked at {datetime.now(UTC).isoformat()}",
            branch_id=str(uuid.uuid4())
        )
        
        self.append(entry)
        
        if label:
            self.set_label(label, entry.id)
        
        return entry.id
    
    def set_label(self, label: str, entry_id: str) -> None:
        """
        Set label for entry
        
        Args:
            label: Label name
            entry_id: Entry ID
        """
        self.labels[label] = entry_id
        
        # Save labels to separate file
        labels_path = self.session_path.with_suffix(".labels.json")
        try:
            with open(labels_path, "w") as f:
                json.dump(self.labels, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving labels: {e}", exc_info=True)
    
    def get_label(self, label: str) -> str | None:
        """
        Get entry ID for label
        
        Args:
            label: Label name
            
        Returns:
            Entry ID or None if not found
        """
        return self.labels.get(label)
    
    def restore_branch(self, entry_id: str) -> list[MessageEntry]:
        """
        Restore branch up to entry
        
        Args:
            entry_id: Entry to restore to
            
        Returns:
            List of messages in restored branch
        """
        return self.get_messages_in_branch(entry_id)
    
    def get_latest_entry(self) -> SessionEntry | None:
        """Get latest entry in session"""
        return self.entries[-1] if self.entries else None
    
    def get_entry(self, entry_id: str) -> SessionEntry | None:
        """Get entry by ID"""
        return self.entry_map.get(entry_id)
    
    def get_children(self, entry_id: str) -> list[SessionEntry]:
        """Get child entries"""
        return [e for e in self.entries if e.parent_id == entry_id]
    
    def get_tree_structure(self) -> dict[str, Any]:
        """
        Get tree structure for visualization
        
        Returns:
            Tree structure as nested dict
        """
        # Build tree
        tree: dict[str, Any] = {}
        
        def build_node(entry_id: str) -> dict[str, Any]:
            entry = self.entry_map.get(entry_id)
            if not entry:
                return {}
            
            children = self.get_children(entry_id)
            
            return {
                "id": entry.id,
                "type": entry.type,
                "timestamp": entry.timestamp,
                "children": [build_node(child.id) for child in children]
            }
        
        # Find root entries (no parent)
        roots = [e for e in self.entries if e.parent_id is None]
        
        tree["roots"] = [build_node(root.id) for root in roots]
        tree["total_entries"] = len(self.entries)
        tree["labels"] = self.labels
        
        return tree
    
    def export_messages(self, entry_id: str | None = None) -> list[dict[str, Any]]:
        """
        Export messages in standard format
        
        Args:
            entry_id: Entry to export from (None for all)
            
        Returns:
            List of message dicts
        """
        messages = self.get_messages_in_branch(entry_id)
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "tool_calls": msg.tool_calls,
                "tool_call_id": msg.tool_call_id,
                "metadata": msg.metadata,
            }
            for msg in messages
        ]
