"""Configuration schema using Pydantic"""

from pydantic import BaseModel, Field


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
    """Gateway server configuration"""

    port: int = Field(default=18789)
    bind: str = Field(default="loopback")
    mode: str = Field(default="local")
    auth: AuthConfig | None = Field(default=None)


class ToolsConfig(BaseModel):
    """Tools configuration"""

    profile: str = Field(default="full")
    allow: list[str] | None = Field(default=None)
    deny: list[str] | None = Field(default=None)


class AgentDefaults(BaseModel):
    """Default agent settings"""

    workspace: str | None = Field(default=None)
    agentDir: str | None = Field(default=None)
    model: str | ModelConfig = Field(default="anthropic/claude-opus-4-5-20250514")
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

    defaults: AgentDefaults | None = Field(default=None)
    agents: list[AgentEntry] | None = Field(default_factory=list)


class ChannelConfig(BaseModel):
    """Individual channel configuration"""

    enabled: bool = Field(default=True)
    allowFrom: list[str] | None = Field(default=None)


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


class ClawdbotConfig(BaseModel):
    """Root configuration schema"""

    agent: AgentConfig | None = Field(default_factory=AgentConfig)
    gateway: GatewayConfig | None = Field(default_factory=GatewayConfig)
    agents: AgentsConfig | None = Field(default_factory=AgentsConfig)
    channels: ChannelsConfig | None = Field(default_factory=ChannelsConfig)
    tools: ToolsConfig | None = Field(default_factory=ToolsConfig)
    skills: SkillsConfig | None = Field(default_factory=SkillsConfig)
    plugins: PluginsConfig | None = Field(default_factory=PluginsConfig)

    class Config:
        extra = "allow"  # Allow extra fields for extensibility
