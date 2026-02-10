"""Built-in command definitions"""
from .commands_registry_types import Command, CommandScope, CommandDispatchMode


# Built-in commands
BUILTIN_COMMANDS = [
    Command(
        name="new",
        aliases=["reset", "clear"],
        description="Start a new conversation (reset session)",
        usage="/new",
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="status",
        aliases=["info", "state"],
        description="Show current agent status and configuration",
        usage="/status",
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="model",
        description="Switch to a different LLM model",
        usage="/model [model_name]",
        examples=[
            "/model gpt-4",
            "/model claude-3-opus",
            "/model gemini-pro",
        ],
        requires_args=True,
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="think",
        description="Enable extended thinking mode",
        usage="/think [on|off]",
        examples=[
            "/think on",
            "/think off",
        ],
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="config",
        description="Show or update agent configuration",
        usage="/config [key] [value]",
        examples=[
            "/config",  # Show all
            "/config temperature 0.7",
            "/config max_tokens 2000",
        ],
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="help",
        aliases=["?", "commands"],
        description="Show available commands",
        usage="/help [command]",
        examples=[
            "/help",
            "/help model",
        ],
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="history",
        description="Show conversation history",
        usage="/history [limit]",
        examples=[
            "/history",
            "/history 10",
        ],
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="retry",
        aliases=["again"],
        description="Retry last message with different response",
        usage="/retry",
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="debug",
        description="Toggle debug mode",
        usage="/debug [on|off]",
        admin_only=True,
        dispatch_mode=CommandDispatchMode.HANDLER,
    ),
    Command(
        name="exec",
        description="Execute code (admin only)",
        usage="/exec [code]",
        admin_only=True,
        requires_args=True,
        dispatch_mode=CommandDispatchMode.HANDLER,
        hidden=True,  # Don't show in help
    ),
]


def get_builtin_commands() -> list[Command]:
    """Get all built-in commands"""
    return BUILTIN_COMMANDS.copy()
