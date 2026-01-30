"""Skill types and structures"""

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
