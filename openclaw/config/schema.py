"""Configuration schema using Pydantic (aligned with TypeScript OpenClawConfig)"""

from pydantic import BaseModel, Field
from typing import Any


class ModelConfig(BaseModel):
    """Model configuration"""
    primary: str = Field(default="anthropic/claude-opus-4-5-20250514")
    fallbacks: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Agent configuration"""
    model: str | ModelConfig = Field(default="anthropic/claude-opus-4-5-20250514")
    thinking: str | None = Field(default=None)
    verbose: bool = Field(default=False)


class AuthConfig(BaseModel):
    """Gateway authentication configuration"""
    mode: str = Field(default="token")
    token: str | None = Field(default=None)
    password: str | None = Field(default=None)


class GatewayConfig(BaseModel):
    """Gateway server configuration (aligned with TypeScript)"""
    port: int = Field(default=18789)
    bind: str = Field(default="loopback")
    mode: str = Field(default="local")
    auth: AuthConfig | None = Field(default=None)
    enable_web_ui: bool = Field(default=True, alias="enableWebUI")
    web_ui_port: int = Field(default=8080, alias="webUIPort")
    web_ui_base_path: str = Field(default="/", alias="webUIBasePath")


class ExecToolConfig(BaseModel):
    """Exec tool configuration"""
    host: str = Field(default="gateway")
    security: str = Field(default="full")
    ask: str = Field(default="off")
    safe_bins: list[str] = Field(default_factory=lambda: ["python", "pip", "git", "node", "npm"])
    path_prepend: list[str] = Field(default_factory=list)
    timeout_sec: int = Field(default=120)


class ToolsConfig(BaseModel):
    """Tools configuration (aligned with TypeScript)"""
    profile: str = Field(default="full")
    allow: list[str] | None = Field(default=None)
    deny: list[str] | None = Field(default=None)
    exec: ExecToolConfig | None = Field(default_factory=ExecToolConfig)


class AgentDefaults(BaseModel):
    """Default agent settings"""

    workspace: str | None = Field(default=None)
    agentDir: str | None = Field(default=None)
    model: str | ModelConfig = Field(default="google/gemini-3-pro-preview")
    tools: ToolsConfig | None = Field(default=None)


class AgentEntry(BaseModel):
    """Individual agent configuration"""

    id: str
    name: str | None = Field(default=None)
    workspace: str | None = Field(default=None)
    agentDir: str | None = Field(default=None)
    model: str | ModelConfig | None = Field(default=None)
    tools: ToolsConfig | None = Field(default=None)


class AgentsConfig(BaseModel):
    """Agents configuration"""

    defaults: AgentDefaults = Field(default_factory=AgentDefaults)
    agents: list[AgentEntry] | None = Field(default_factory=list)


class ChannelConfig(BaseModel):
    """Individual channel configuration"""

    enabled: bool = Field(default=True)
    botToken: str | None = Field(default=None)
    allowFrom: list[str] | None = Field(default=None)
    dmPolicy: str | None = Field(default=None)
    
    # Additional platform-specific fields
    token: str | None = Field(default=None)  # Generic token field
    signingSecret: str | None = Field(default=None)  # Slack
    appId: str | None = Field(default=None)  # Teams/Facebook
    appSecret: str | None = Field(default=None)


class ChannelsConfig(BaseModel):
    """Channels configuration"""

    telegram: ChannelConfig | None = Field(default=None)
    whatsapp: ChannelConfig | None = Field(default=None)
    discord: ChannelConfig | None = Field(default=None)
    slack: ChannelConfig | None = Field(default=None)


class SkillsConfig(BaseModel):
    """Skills configuration"""

    allowBundled: list[str] | None = Field(default=None)
    enable: list[str] | None = Field(default=None)
    disable: list[str] | None = Field(default=None)


class PluginsConfig(BaseModel):
    """Plugins configuration"""

    enable: list[str] | None = Field(default=None)
    disable: list[str] | None = Field(default=None)


class MetaConfig(BaseModel):
    """Metadata configuration"""
    last_touched_version: str | None = Field(default=None, alias="lastTouchedVersion")
    last_touched_at: str | None = Field(default=None, alias="lastTouchedAt")


class WizardConfig(BaseModel):
    """Wizard run tracking"""
    last_run_at: str | None = Field(default=None, alias="lastRunAt")
    last_run_version: str | None = Field(default=None, alias="lastRunVersion")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO")
    format: str = Field(default="colored")


class UpdateConfig(BaseModel):
    """Update configuration"""
    channel: str = Field(default="stable")
    check_on_start: bool = Field(default=False, alias="checkOnStart")


class UIConfig(BaseModel):
    """UI configuration"""
    seam_color: str | None = Field(default=None, alias="seamColor")


class ModelsConfig(BaseModel):
    """Models configuration"""
    providers: dict[str, Any] | None = Field(default=None)


class MemoryConfig(BaseModel):
    """Memory configuration"""
    enabled: bool = Field(default=True)
    provider: str = Field(default="simple")


class CronConfig(BaseModel):
    """Cron configuration"""
    enabled: bool = Field(default=True)


class HooksConfig(BaseModel):
    """Hooks configuration"""
    enabled: bool = Field(default=True)


class ClawdbotConfig(BaseModel):
    """Root configuration schema (aligned with TypeScript OpenClawConfig)"""
    
    # Core configs (original 7)
    agent: AgentConfig | None = Field(default_factory=AgentConfig)
    gateway: GatewayConfig | None = Field(default_factory=GatewayConfig)
    agents: AgentsConfig | None = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig | None = Field(default_factory=ChannelsConfig)
    tools: ToolsConfig | None = Field(default_factory=ToolsConfig)
    skills: SkillsConfig | None = Field(default_factory=SkillsConfig)
    plugins: PluginsConfig | None = Field(default_factory=PluginsConfig)
    
    # Additional configs (matching TypeScript - 21 more fields)
    meta: MetaConfig | None = Field(default=None)
    auth: dict[str, Any] | None = Field(default=None)
    env: dict[str, Any] | None = Field(default=None)
    wizard: WizardConfig | None = Field(default=None)
    diagnostics: dict[str, Any] | None = Field(default=None)
    logging: LoggingConfig | None = Field(default=None)
    update: UpdateConfig | None = Field(default=None)
    browser: dict[str, Any] | None = Field(default=None)
    ui: UIConfig | None = Field(default=None)
    models: ModelsConfig | None = Field(default=None)
    node_host: dict[str, Any] | None = Field(default=None, alias="nodeHost")
    bindings: list[dict[str, Any]] | None = Field(default=None)
    broadcast: dict[str, Any] | None = Field(default=None)
    audio: dict[str, Any] | None = Field(default=None)
    messages: dict[str, Any] | None = Field(default=None)
    commands: dict[str, Any] | None = Field(default=None)
    approvals: dict[str, Any] | None = Field(default=None)
    session: dict[str, Any] | None = Field(default=None)
    web: dict[str, Any] | None = Field(default=None)
    cron: CronConfig | None = Field(default=None)
    hooks: HooksConfig | None = Field(default=None)
    discovery: dict[str, Any] | None = Field(default=None)
    canvas_host: dict[str, Any] | None = Field(default=None, alias="canvasHost")
    talk: dict[str, Any] | None = Field(default=None)
    memory: MemoryConfig | None = Field(default=None)

    class Config:
        extra = "allow"  # Allow extra fields for extensibility
        populate_by_name = True  # Support camelCase aliases
