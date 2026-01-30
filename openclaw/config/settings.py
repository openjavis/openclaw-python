"""
Enhanced configuration with Pydantic settings
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseModel):
    """Agent configuration"""

    model: str = Field(default="anthropic/claude-opus-4", description="LLM model to use")
    api_key: str | None = Field(default=None, description="API key (uses env var if not set)")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    enable_context_management: bool = Field(
        default=True, description="Enable automatic context management"
    )
    max_tokens: int = Field(default=4096, gt=0, description="Maximum tokens per response")


class ToolsConfig(BaseModel):
    """Tools configuration"""

    timeout_seconds: float = Field(default=30.0, gt=0, description="Default tool timeout")
    max_output_size: int = Field(default=100000, gt=0, description="Maximum tool output size")
    rate_limit_per_minute: int | None = Field(
        default=None, ge=1, description="Rate limit for tools"
    )
    sandbox_enabled: bool = Field(default=False, description="Enable sandbox execution")


class ChannelConfig(BaseModel):
    """Channel configuration"""

    enabled: list[str] = Field(default_factory=list, description="List of enabled channel IDs")
    auto_reconnect: bool = Field(default=True, description="Enable automatic reconnection")
    max_reconnect_attempts: int = Field(
        default=10, ge=1, description="Maximum reconnection attempts"
    )
    health_check_interval: float = Field(
        default=60.0, gt=0, description="Health check interval in seconds"
    )


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""

    enabled: bool = Field(default=True, description="Enable monitoring")
    health_checks: bool = Field(default=True, description="Enable health checks")
    metrics_collection: bool = Field(default=True, description="Enable metrics collection")
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="colored", description="Log format (colored, json, simple)")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format"""
        valid_formats = ["colored", "json", "simple"]
        if v not in valid_formats:
            raise ValueError(f"Log format must be one of {valid_formats}")
        return v


class APIConfig(BaseModel):
    """API server configuration"""

    enabled: bool = Field(default=True, description="Enable API server")
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, ge=1, le=65535, description="API server port")
    api_key: str | None = Field(default=None, description="API authentication key")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"], description="CORS allowed origins"
    )


class GatewayConfig(BaseModel):
    """Gateway WebSocket server configuration"""

    enabled: bool = Field(default=True, description="Enable gateway server")
    host: str = Field(default="0.0.0.0", description="Gateway server host")
    port: int = Field(default=3000, ge=1, le=65535, description="Gateway server port")
    auth_required: bool = Field(default=True, description="Require authentication")


class Settings(BaseSettings):
    """
    Main application settings

    Automatically loads from:
    1. Environment variables (CLAWDBOT_*)
    2. .env file
    3. Default values
    """

    model_config = SettingsConfigDict(
        env_prefix="CLAWDBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Workspace
    workspace_dir: Path = Field(
        default=Path("./workspace"), description="Workspace directory for sessions and data"
    )

    # Component configurations
    agent: AgentConfig = Field(default_factory=AgentConfig, description="Agent configuration")

    tools: ToolsConfig = Field(default_factory=ToolsConfig, description="Tools configuration")

    channels: ChannelConfig = Field(
        default_factory=ChannelConfig, description="Channels configuration"
    )

    monitoring: MonitoringConfig = Field(
        default_factory=MonitoringConfig, description="Monitoring configuration"
    )

    api: APIConfig = Field(default_factory=APIConfig, description="API server configuration")

    gateway: GatewayConfig = Field(
        default_factory=GatewayConfig, description="Gateway server configuration"
    )

    # Additional settings
    debug: bool = Field(default=False, description="Enable debug mode")

    @field_validator("workspace_dir")
    @classmethod
    def create_workspace(cls, v: Path) -> Path:
        """Create workspace directory if it doesn't exist"""
        v = v.expanduser().absolute()
        v.mkdir(parents=True, exist_ok=True)
        return v

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary"""
        return self.model_dump()

    def save_to_file(self, path: Path) -> None:
        """Save settings to JSON file"""
        import json

        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def load_from_file(cls, path: Path) -> "Settings":
        """Load settings from JSON file"""
        import json

        with open(path) as f:
            data = json.load(f)
        return cls(**data)


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment/files"""
    global _settings
    _settings = Settings()
    return _settings


# Convenience functions
def get_workspace_dir() -> Path:
    """Get workspace directory"""
    return get_settings().workspace_dir


def get_agent_config() -> AgentConfig:
    """Get agent configuration"""
    return get_settings().agent


def get_api_config() -> APIConfig:
    """Get API configuration"""
    return get_settings().api
