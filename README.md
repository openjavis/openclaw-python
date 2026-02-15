# OpenXJarvis (openclaw-python)

> A Python implementation of the OpenClaw AI assistant platform, actively aligned with the TypeScript version

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**OpenXJarvis** is a complete Python port of OpenClaw, connecting messaging channels (Telegram, Discord, Slack) with AI models (Claude, GPT, Gemini). Built with Python's strengths for clarity and maintainability.

## ⚠️ Development Status

**This is an active development version.** We are continuously improving and aligning with the TypeScript OpenClaw implementation. Features and APIs may change as we reach feature parity.

**Recent Improvements:**
- ✅ Session management aligned with TypeScript (UUID-based, proper reset functionality)
- ✅ History limiting system (prevents context overload)
- ✅ Enhanced message handling and tool execution
- ✅ Context pruning and sanitization
- 🔄 Ongoing: Full feature parity with TypeScript OpenClaw

**Current Status:**
- **✅ Working:** Telegram integration, core agent runtime, 24+ built-in tools, 56+ skills
- **🔨 In Progress:** Discord/Slack channels, Web UI, voice integration

## Quick Start

### Prerequisites

- **Python 3.11+** (3.12+ recommended)
- **uv** package manager
- At least one LLM API key (Anthropic Claude, OpenAI, or Google Gemini)
- **For Telegram:** Bot token from [@BotFather](https://t.me/botfather)

### Installation

```bash
# Install uv package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/openxjarvis/openclaw-python.git
cd openclaw-python

# Install dependencies
uv sync
```

### Configuration

1. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Add your API keys to `.env`:**
   ```bash
   # Required: At least one AI model provider
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   # OR
   OPENAI_API_KEY=sk-your-key-here
   # OR
   GOOGLE_API_KEY=your-google-key-here

   # Required for Telegram integration
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   ```

3. **Run initial setup:**
   ```bash
   # Interactive onboarding wizard (recommended)
   uv run openclaw onboard
   
   # Quick setup with auto-daemon installation
   uv run openclaw onboard --flow quickstart --install-daemon
   ```

## Command Reference

### Gateway Operations

The gateway is the core server that manages channels and AI agent runtime.

#### Start Gateway

```bash
# Development mode (foreground, see logs directly)
uv run openclaw start --port 18789 --telegram

# As background service (recommended for production)
uv run openclaw gateway install  # Install service
uv run openclaw gateway start    # Start service
```

**Options for `start` command:**
- `--port PORT` - Gateway port (default: 18789)
- `--telegram` - Enable Telegram channel
- `--discord` - Enable Discord channel (in development)
- `--slack` - Enable Slack channel (in development)

#### Access Web Control UI

Once the gateway is running, you can access the Web Control UI:

```bash
# Gateway must be running first
uv run openclaw start --telegram

# Open in browser
http://localhost:18789
```

**Build Web UI (if needed):**

If the UI files are not built, you'll see a message to build them:

```bash
# Navigate to UI source directory
cd openclaw/web/ui-src

# Install dependencies
npm install

# Build for production
npm run build

# Or run in development mode
npm run dev
```

The gateway automatically serves the built UI files from `openclaw/web/dist/`.

#### Manage Gateway

```bash
# Check gateway status
uv run openclaw gateway status

# View live logs
uv run openclaw gateway logs

# Restart gateway
uv run openclaw gateway restart

# Stop gateway
uv run openclaw gateway stop

# Uninstall service
uv run openclaw gateway uninstall
```

#### Troubleshooting

```bash
# Run system diagnostics
uv run openclaw doctor

# Kill all processes (use when gateway is stuck)
uv run openclaw cleanup --kill-all

# Clean up specific ports
uv run openclaw cleanup --ports 18789

# Show current configuration
uv run openclaw config show
```

### Session Management

Sessions track conversation history. The new session system uses UUIDs for proper isolation.

```bash
# Reset current session (start fresh conversation)
# Send "/reset" in your Telegram chat

# Sessions are stored at: ~/.openclaw/agents/main/sessions/
# Each session has a UUID filename (e.g., 497700f3-7d22-439f-8eb8-a7e1013cf726.json)
```

### Channel Management

```bash
# List available channels
uv run openclaw channels list

# Currently operational: Telegram only
# Discord, Slack, WhatsApp: In development
```

### Access Control (Pairing)

Control who can interact with your bot via Telegram.

```bash
# View pending pairing requests
uv run openclaw pairing list telegram

# Approve a user's access request
uv run openclaw pairing approve telegram <code>

# View approved users (allowlist)
uv run openclaw pairing allowlist telegram

# Deny a request
uv run openclaw pairing deny telegram <code>

# Revoke access
uv run openclaw pairing revoke telegram <user_id>
```

**DM Policy Configuration:**

Edit `~/.openclaw/config.json` to set policy:
- `"pairing"` (default) - Requires manual approval
- `"allowlist"` - Only pre-approved users
- `"open"` - Any user (requires `allow_from: ["*"]`)
- `"disabled"` - No DM access

### Configuration Commands

```bash
# View current configuration
uv run openclaw config show

# Edit configuration file
# Location: ~/.openclaw/config.json
```

## Using with Telegram

### Setup Steps

1. **Create a Telegram bot:**
   - Open Telegram and message [@BotFather](https://t.me/botfather)
   - Send `/newbot` command
   - Follow prompts to set bot name and username
   - Copy the provided bot token

2. **Configure bot token:**
   ```bash
   # Add to .env file
   TELEGRAM_BOT_TOKEN=your-bot-token-here
   ```

3. **Start the gateway:**
   ```bash
   uv run openclaw start --telegram
   ```

4. **Interact with your bot:**
   - Find your bot on Telegram by username
   - Start a conversation
   - The bot has access to tools and can execute commands

### Reset Session

To start a fresh conversation (clear history):
```
/reset
```

This creates a new session with a clean slate - no previous conversation history.

## Architecture

```
openclaw-python/
├── openclaw/
│   ├── agents/              # Agent runtime and execution
│   │   ├── tools/           # 24+ built-in tools
│   │   ├── extensions/      # Context pruning, etc.
│   │   └── providers/       # LLM provider integrations
│   ├── channels/            # Communication channels
│   │   └── telegram/        # ✅ Fully operational
│   ├── gateway/             # WebSocket gateway server
│   │   ├── api/             # RPC method handlers
│   │   └── protocol/        # Protocol definitions
│   ├── skills/              # 56+ modular skills
│   ├── config/              # Configuration management
│   │   └── sessions/        # Session store and management
│   ├── routing/             # Message routing and session keys
│   └── cli/                 # Command-line interface
└── tests/                   # Test suite
```

## Workspace Files

Your workspace at `~/.openclaw/workspace/` contains agent configuration:

- **SOUL.md** - Agent personality, values, and behavior
- **AGENTS.md** - Operating instructions and guidelines
- **TOOLS.md** - Tool availability and configurations
- **USER.md** - User profile and preferences
- **IDENTITY.md** - Agent identity and capabilities

These markdown files are injected into the agent's system prompt, shaping its behavior and responses.

## Development

```bash
# Run test suite
uv run pytest

# Run specific test file
uv run pytest tests/test_session_reset_alignment.py

# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking (if mypy configured)
uv run mypy openclaw/
```

## File Structure

```
~/.openclaw/                      # Configuration directory
├── config.json                   # Main configuration
├── workspace/                    # Agent workspace
│   ├── SOUL.md                  # Personality
│   ├── AGENTS.md                # Instructions
│   └── ...
├── agents/
│   └── main/
│       └── sessions/            # Session storage (UUID-based)
│           ├── <uuid>.json      # Session files
│           └── sessions.json    # Session index
└── logs/
    └── gateway.out.log          # Gateway logs
```

## Alignment with TypeScript OpenClaw

We are actively working to align this Python implementation with the TypeScript OpenClaw:

**Recently Aligned:**
- ✅ Session key format: `agent:main:telegram:dm:<chat_id>`
- ✅ UUID-based session IDs (changes on reset)
- ✅ Session file paths: `~/.openclaw/agents/main/sessions/<uuid>.json`
- ✅ History limiting (prevents context overflow)
- ✅ Context pruning and sanitization
- ✅ Tool execution and follow-up handling
- ✅ Gateway protocol and RPC methods

**In Progress:**
- 🔄 Web Control UI
- 🔄 Additional channel integrations
- 🔄 Advanced automation features
- 🔄 Voice integration

## Contributing

This project is under active development. While we welcome interest, please note that APIs and features are still evolving as we work toward full OpenClaw compatibility.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Credits

This is a Python port of the original [OpenClaw](https://github.com/openjavis/openclaw) TypeScript project by the OpenJavis team.

## Links

- [OpenClaw (TypeScript)](https://github.com/openjavis/openclaw) - Original implementation
- [Issue Tracker](https://github.com/openxjarvis/openclaw-python/issues)
- [Telegram BotFather](https://t.me/botfather) - Create Telegram bots

---

**Status**: Active Development • Telegram Ready • Aligning with OpenClaw TypeScript  
**Python**: 3.11+ required, 3.12+ recommended  
**Updates**: Frequent improvements and fixes
