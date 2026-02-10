"""
Skills type definitions

Matches TypeScript src/agents/skills/types.ts
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Skill:
    """
    Skill definition (matches @mariozechner/pi-coding-agent).
    
    Attributes:
        name: Skill name
        description: Skill description
        location: Path to SKILL.md file
        source: Source identifier (bundled, managed, workspace)
    """
    name: str
    description: str
    location: str
    source: str = "unknown"


@dataclass
class SkillInstallSpec:
    """
    Installation specification (matches TS SkillInstallSpec).
    
    Attributes:
        kind: Installation kind (brew|node|go|uv|download)
        id: Optional install ID
        label: Display label
        bins: Required binaries
        os: Supported operating systems
        formula: Homebrew formula name
        package: Package name (npm/pip/etc)
        module: Module name
        url: Download URL
        archive: Archive name
        extract: Extract archive
        strip_components: Strip path components
        target_dir: Target directory
    """
    kind: str  # brew | node | go | uv | download
    id: str | None = None
    label: str | None = None
    bins: list[str] = field(default_factory=list)
    os: list[str] = field(default_factory=list)
    formula: str | None = None
    package: str | None = None
    module: str | None = None
    url: str | None = None
    archive: str | None = None
    extract: bool = False
    strip_components: int = 0
    target_dir: str | None = None


@dataclass
class OpenClawSkillMetadata:
    """
    OpenClaw-specific skill metadata (matches TS OpenClawSkillMetadata).
    
    Attributes:
        always: Always include this skill
        skill_key: Unique skill key
        primary_env: Primary environment variable
        emoji: Skill emoji icon
        homepage: Skill homepage URL
        os: Supported operating systems
        requires: Requirements (bins, env, config)
        install: Installation specifications
    """
    always: bool = False
    skill_key: str | None = None
    primary_env: str | None = None
    emoji: str | None = None
    homepage: str | None = None
    os: list[str] = field(default_factory=list)
    requires: dict[str, list[str]] = field(default_factory=dict)
    install: list[SkillInstallSpec] = field(default_factory=list)


@dataclass
class SkillInvocationPolicy:
    """
    Skill invocation policy (matches TS SkillInvocationPolicy).
    
    Attributes:
        user_invocable: Can be invoked by user
        disable_model_invocation: Disable model invocation
    """
    user_invocable: bool = True
    disable_model_invocation: bool = False


@dataclass
class SkillCommandDispatch:
    """
    Skill command dispatch specification (matches TS SkillCommandDispatchSpec).
    
    Attributes:
        kind: Dispatch kind (currently only "tool")
        tool_name: Name of tool to invoke
        arg_mode: Argument mode ("raw" | "parsed")
    """
    kind: str = "tool"  # Currently only "tool"
    tool_name: str = ""
    arg_mode: str = "parsed"  # "raw" | "parsed"


@dataclass
class SkillCommandSpec:
    """
    Skill command specification (matches TS SkillCommandSpec).
    
    Attributes:
        name: Command name (e.g., /summarize)
        skill_name: Corresponding skill name
        description: Command description
        dispatch: Optional dispatch configuration
    """
    name: str
    skill_name: str
    description: str
    dispatch: SkillCommandDispatch | None = None


@dataclass
class SkillEntry:
    """
    Skill with metadata (matches TS SkillEntry).
    
    Attributes:
        skill: The skill definition
        frontmatter: Parsed YAML frontmatter
        metadata: OpenClaw-specific metadata
        invocation: Invocation policy
    """
    skill: Skill
    frontmatter: dict[str, Any]
    metadata: OpenClawSkillMetadata | None = None
    invocation: SkillInvocationPolicy | None = None


@dataclass
class SkillEligibilityContext:
    """
    Context for skill eligibility checking (matches TS SkillEligibilityContext).
    
    Attributes:
        remote: Remote environment info (platforms, binary checks)
    """
    remote: dict[str, Any] | None = None


@dataclass
class SkillSnapshot:
    """
    Skills snapshot for prompt (matches TS SkillSnapshot).
    
    Attributes:
        prompt: Formatted skills prompt
        skills: List of skill info (name, primaryEnv)
        resolved_skills: Resolved skill objects
        version: Snapshot version
    """
    prompt: str
    skills: list[dict[str, str]]
    resolved_skills: list[Skill] | None = None
    version: int = 1


@dataclass
class SkillsInstallPreferences:
    """
    Installation preferences (matches TS SkillsInstallPreferences).
    
    Attributes:
        prefer_brew: Prefer Homebrew installation
        node_manager: Node package manager (npm|pnpm|yarn|bun)
    """
    prefer_brew: bool = True
    node_manager: str = "npm"  # npm | pnpm | yarn | bun
