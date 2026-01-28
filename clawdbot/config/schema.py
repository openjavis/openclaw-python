"""Configuration schema using Pydantic"""

from typing import Any, Optional, Union
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model configuration"""

    primary: str = Field(default="anthropic/claude-opus-4-5-20250514")
    fallbacks: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    """Agent configuration"""

    model: Union[str, ModelConfig] = Field(default="anthropic/claude-opus-4-5-20250514")
    thinking: Optional[str] = Field(default=None)
    verbose: bool = Field(default=False)


class AuthConfig(BaseModel):
    """Gateway authentication configuration"""

    mode: str = Field(default="token")
    token: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)


class GatewayConfig(BaseModel):
    """Gateway server configuration"""

    port: int = Field(default=18789)
    bind: str = Field(default="loopback")
    mode: str = Field(default="local")
    auth: Optional[AuthConfig] = Field(default=None)


class ToolsConfig(BaseModel):
    """Tools configuration"""

    profile: str = Field(default="full")
    allow: Optional[list[str]] = Field(default=None)
    deny: Optional[list[str]] = Field(default=None)


class AgentDefaults(BaseModel):
    """Default agent settings"""

    workspace: Optional[str] = Field(default=None)
    agentDir: Optional[str] = Field(default=None)
    model: Union[str, ModelConfig] = Field(default="anthropic/claude-opus-4-5-20250514")
    tools: Optional[ToolsConfig] = Field(default=None)


class AgentEntry(BaseModel):
    """Individual agent configuration"""

    id: str
    name: Optional[str] = Field(default=None)
    workspace: Optional[str] = Field(default=None)
    agentDir: Optional[str] = Field(default=None)
    model: Optional[Union[str, ModelConfig]] = Field(default=None)
    tools: Optional[ToolsConfig] = Field(default=None)


class AgentsConfig(BaseModel):
    """Agents configuration"""

    defaults: Optional[AgentDefaults] = Field(default=None)
    agents: Optional[list[AgentEntry]] = Field(default_factory=list)


class ChannelConfig(BaseModel):
    """Individual channel configuration"""

    enabled: bool = Field(default=True)
    allowFrom: Optional[list[str]] = Field(default=None)


class ChannelsConfig(BaseModel):
    """Channels configuration"""

    telegram: Optional[ChannelConfig] = Field(default=None)
    whatsapp: Optional[ChannelConfig] = Field(default=None)
    discord: Optional[ChannelConfig] = Field(default=None)
    slack: Optional[ChannelConfig] = Field(default=None)


class SkillsConfig(BaseModel):
    """Skills configuration"""

    allowBundled: Optional[list[str]] = Field(default=None)
    enable: Optional[list[str]] = Field(default=None)
    disable: Optional[list[str]] = Field(default=None)


class PluginsConfig(BaseModel):
    """Plugins configuration"""

    enable: Optional[list[str]] = Field(default=None)
    disable: Optional[list[str]] = Field(default=None)


class ClawdbotConfig(BaseModel):
    """Root configuration schema"""

    agent: Optional[AgentConfig] = Field(default_factory=AgentConfig)
    gateway: Optional[GatewayConfig] = Field(default_factory=GatewayConfig)
    agents: Optional[AgentsConfig] = Field(default_factory=AgentsConfig)
    channels: Optional[ChannelsConfig] = Field(default_factory=ChannelsConfig)
    tools: Optional[ToolsConfig] = Field(default_factory=ToolsConfig)
    skills: Optional[SkillsConfig] = Field(default_factory=SkillsConfig)
    plugins: Optional[PluginsConfig] = Field(default_factory=PluginsConfig)

    class Config:
        extra = "allow"  # Allow extra fields for extensibility
