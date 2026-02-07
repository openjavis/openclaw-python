"""Skill types and structures"""

from typing import Any

from pydantic import BaseModel


class SkillMetadata(BaseModel):
    """Skill metadata from frontmatter"""

    name: str
    description: str | None = None
    version: str | None = None
    author: str | None = None
    tags: list[str] = []
    requires_bins: list[str] = []
    requires_env: list[str] = []
    requires_config: list[str] = []
    os: list[str] | None = None  # ["darwin", "linux", "windows"]

    # Provide dict-like `.get()` for compatibility with existing code/tests
    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        try:
            return getattr(self, key, default)
        except Exception:
            try:
                return self.model_dump().get(key, default)
            except Exception:
                return default


class Skill(BaseModel):
    """A skill entry"""

    name: str
    content: str  # The skill prompt content
    metadata: SkillMetadata
    source: str  # "bundled", "managed", "workspace", "plugin"
    path: str  # File path


class SkillInvocationPolicy(BaseModel):
    """Skill invocation policy"""

    user_invocable: bool = True
    disable_model_invocation: bool = False
