"""Memory system types."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MemorySource(Enum):
    """Source of memory content."""
    MEMORY = "memory"
    SESSION = "session"
    CUSTOM = "custom"


@dataclass
class MemorySearchResult:
    """Result from memory search."""
    id: str
    path: str
    source: MemorySource
    text: str
    snippet: str
    start_line: int
    end_line: int
    score: float
    distance: Optional[float] = None  # For vector search
    
    def __repr__(self) -> str:
        return f"MemorySearchResult(path={self.path}, lines={self.start_line}-{self.end_line}, score={self.score:.3f})"
