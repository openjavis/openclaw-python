# OpenXJarvis (openclaw-python)

> A full-featured Python implementation of the OpenClaw AI assistant platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**OpenXJarvis** is a complete Python port of OpenClaw, connecting messaging channels (Telegram, Discord, Slack) with AI models (Claude, GPT, Gemini). Built with Python's strengths for clarity and maintainability.

## Current Status

**✅ Working:**
- **Telegram channel integration** (fully operational)
- Core agent runtime with tool execution
- 24 built-in tools (file operations, web search, bash, etc.)
- 56+ skills for specialized tasks
- Multi-model support (Claude, GPT, Gemini)

**🔨 In Development:**
- Discord, Slack, and WhatsApp channels
- Web Control UI
- Voice integration
- Advanced automation features

## Quick Start

### Prerequisites

- **Python 3.11+** (3.12+ recommended)
- **uv** package manager
- At least one LLM API key (Anthropic, OpenAI, or Google Gemini)
- **For Telegram:** A bot token from [@BotFather](https://t.me/botfather)

### Installation

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/openxjarvis/openclaw-python.git
cd openclaw-python

# Install dependencies
uv sync
```

### Configuration

1. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Add your API keys:**
   ```bash
   # Required: At least one AI model provider
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   # OR
   OPENAI_API_KEY=sk-your-key-here
   # OR
   GOOGLE_API_KEY=your-google-key-here

   # Required for Telegram
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   ```

3. **Run initial setup:**
   ```bash
   # Interactive wizard (recommended)
   uv run openclaw onboard
   
   # QuickStart mode (auto-install Gateway service)
   uv run openclaw onboard --flow quickstart --install-daemon
   ```

## Command Reference

### Starting the Gateway

```bash
# Option 1: Auto-install during onboarding (recommended)
uv run openclaw onboard --install-daemon

# Option 2: Manual service installation
uv run openclaw gateway install
uv run openclaw gateway start

# Option 3: Run in foreground (development mode)
uv run openclaw start --port 18789 --telegram
```

### Managing the Gateway

```bash
# Check status
uv run openclaw gateway status

# Stop the gateway
uv run openclaw gateway stop
# Or use:
uv run openclaw cleanup --kill-all

# View logs (if running as service)
uv run openclaw gateway logs

# Clean up stuck ports
uv run openclaw cleanup --ports 18789
```

### Channel Management

```bash
# List available channels
uv run openclaw channels list

# Note: Currently only Telegram is operational
```

### Access Control (Pairing)

Control who can access your bot via Telegram:

```bash
# View pending pairing requests
uv run openclaw pairing list telegram

# Approve a pairing request
uv run openclaw pairing approve telegram <code>

# View allowlist
uv run openclaw pairing allowlist telegram

# Deny a request
uv run openclaw pairing deny telegram <code>
```

**DM Policy Options:**
- `"pairing"` (default) - Requires approval
- `"allowlist"` - Only allowed users
- `"open"` - All users (requires `allow_from: ["*"]`)
- `"disabled"` - No DMs

Edit `~/.openclaw/config.json` to change the policy.

### Troubleshooting

```bash
# Run diagnostics
uv run openclaw doctor

# Check configuration
uv run openclaw config show

# View service logs
tail -f /Users/Shared/.openclaw/logs/gateway.out.log

# Clean up processes
uv run openclaw cleanup --kill-all
```

## Using with Telegram

1. **Create a bot:**
   - Message [@BotFather](https://t.me/botfather)
   - Send `/newbot` and follow prompts
   - Copy your bot token to `.env`

2. **Start the gateway:**
   ```bash
   uv run openclaw start --telegram
   ```

3. **Chat with your bot:**
   - Find your bot on Telegram
   - Send a message to start chatting
   - The agent has access to tools and can execute commands

## Development

```bash
# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint
uv run ruff check .
```

## Architecture

```
openclaw/
├── agents/          # Core agent runtime
│   └── tools/       # Built-in tools (24 tools)
├── channels/        # Communication channels
│   └── telegram/    # ✅ Ready
├── gateway/         # Gateway server
├── skills/          # Modular skills (56+)
├── config/          # Configuration
└── cli/             # Command-line interface
```

## Workspace

Your workspace at `~/.openclaw/workspace/` contains:

- **SOUL.md** - Agent personality and values
- **AGENTS.md** - Operating instructions
- **TOOLS.md** - Tool configurations
- **USER.md** - User profile
- **IDENTITY.md** - Agent identity

These files are injected into the agent's system prompt.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

This is a Python port of the original [OpenClaw](https://github.com/openjavis/openclaw) TypeScript project.

## Links

- [OpenClaw (TypeScript)](https://github.com/openjavis/openclaw)
- [Issue Tracker](https://github.com/openxjarvis/openclaw-python/issues)
- [Telegram BotFather](https://t.me/botfather)

---

**Status**: Telegram Ready • Other Channels In Development  
**Python**: 3.11+ required, 3.12+ recommended
