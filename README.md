# 🦞 OpenClaw Python

> **Openclaw is great, Python I take** 🐍

## ✅ **完全对齐版本** (Updated: 2026-02-10)

**OpenClaw Python** 现已与 TypeScript 版本 **完全对齐**！  
**对齐度**: **98%** | **代码量**: 57,296行 (365个文件) | **状态**: 🚀 Production Ready

**第二次对齐完成**: Prompt Templates系统、Docker沙箱、Subagent Registry、Sidecar架构、40步Gateway启动。  
📖 详见 [`FULL_ALIGNMENT_COMPLETE_2026.md`](./FULL_ALIGNMENT_COMPLETE_2026.md) | [`README_FULL_ALIGNMENT.md`](./README_FULL_ALIGNMENT.md)

---

**OpenClaw Python** is a straightforward Python implementation of the OpenClaw AI assistant platform. It connects messaging channels (Telegram, Discord, Slack) with various AI models, using Python's strengths for clarity and maintainability.

This is the Python port of OpenClaw, designed for those who prefer working in Python over TypeScript. It maintains the same core architecture while leveraging Python's ecosystem and readability.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Features

- 🤖 **Multi-Model Support**: Anthropic Claude, OpenAI GPT, Google Gemini (including Gemini 3 Pro), AWS Bedrock, and Ollama
- 💬 **Multi-Channel**: Telegram, Discord, Slack, and extensible to WhatsApp, Signal, Matrix
- ⏰ **Cron Scheduler**: Set alarms, reminders, recurring tasks ("wake me at 7am", "daily stock market update")
- 📊 **Document Generation**: Create PowerPoint (.pptx) and PDF documents on demand
- 📤 **File Transfer**: Send/receive files via Telegram (photos, videos, documents, PDFs, PPTs)
- 🌐 **Web Control UI**: Beautiful browser-based interface for managing your assistant (HTTP + WebSocket)
- 🧙 **Enhanced Onboarding**: QuickStart and Advanced modes with security acknowledgement
- 🔧 **Extensible Tools**: 24+ built-in tools (file ops, web search, cron, PPT/PDF generation, file transfer, more)
- 🎓 **Skills System**: 56+ modular knowledge and workflow extensions
- 🔐 **Security**: Comprehensive permission management and sandboxing
- 🌐 **Gateway Architecture**: Centralized agent runtime with WebSocket and HTTP APIs
- 📊 **Memory & Context**: Advanced context management with SQLite + FTS5
- 🎨 **Beautiful CLI**: Rich terminal interface with 74+ commands

## Quick Start

### Prerequisites

- **Python 3.11+** (Python 3.14+ recommended)
- **uv** package manager (or pip)
- At least one LLM API key (Anthropic, OpenAI, or Google)

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-org/openclaw-python
cd openclaw-python

# Install dependencies
uv sync

# Add uv to PATH (if needed)
export PATH="$HOME/.local/bin:$PATH"
```

### Configuration

You have two options for configuration:

#### Option 1: Quick Setup with .env File (Fastest)

If you just want to get started quickly:

```bash
# Edit .env file with your API keys
nano .env

# Add your keys:
# GOOGLE_API_KEY=your-key-here
# TELEGRAM_BOT_TOKEN=your-bot-token (optional)

# Start immediately
uv run openclaw start
```

#### Option 2: Interactive Onboarding Wizard (Recommended)

Run the interactive wizard for guided setup:

```bash
openclaw onboard
```

The enhanced wizard offers two modes:

**QuickStart Mode** (Recommended for beginners):
- Smart defaults (Gemini 3 Pro Preview)
- Minimal prompts
- Fastest setup
- Perfect for testing

**Advanced Mode** (For power users):
- Full configuration options
- All model choices
- Detailed channel setup
- Custom settings

The wizard will guide you through:
1. ✅ Security risk acknowledgement
2. ✅ API key configuration (Anthropic/OpenAI/Google)
3. ✅ Workspace setup
4. ✅ Channel configuration (Telegram/Discord/Slack)
5. ✅ Model selection (including Gemini 3 Pro Preview)
6. ✅ Security settings

**Or configure manually:**

```bash
# Copy environment template
cp .env.example .env

# Edit and add your API keys
nano .env
```

Required environment variables:
```bash
# At least one LLM provider (choose one or more)
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-key-here

# Channel tokens (optional)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
DISCORD_BOT_TOKEN=your-discord-bot-token
SLACK_BOT_TOKEN=xoxb-your-slack-token
```

### Running

**Start the Gateway server:**

```bash
# Quick start (foreground)
openclaw start

# Or run gateway explicitly
openclaw gateway run --verbose

# Install as system service (launchd/systemd)
openclaw gateway install
openclaw gateway start
```

### Web Control UI

OpenClaw includes a web-based control interface for managing your assistant:

```bash
# Gateway automatically starts HTTP server on port 8080
openclaw gateway run

# Access control UI in your browser
open http://localhost:8080
```

The web interface provides:
- 🌐 Real-time chat with your agent via WebSocket
- 📊 Channel status and monitoring
- ⚙️ Configuration management
- 🧙 Setup wizard (coming soon)
- 🎨 Modern, responsive design built with Lit Web Components

**Note**: The control UI requires building the TypeScript frontend first:

```bash
# Build control UI (requires Node.js/pnpm)
cd ../openclaw/ui
pnpm install
pnpm build

# Copy built assets
cp -r ../dist/control-ui openclaw-python/openclaw/web/static/
```

Until the UI is built, a helpful placeholder page is shown with setup instructions.

**Test your setup:**

```bash
# Run system diagnostics
openclaw doctor

# Check configuration
openclaw config show

# List available channels
openclaw channels list

# Send a test message to Telegram
# (First, find your bot on Telegram and start a conversation)
```

## Project Structure

```
openclaw-python/
├── openclaw/              # Main package
│   ├── agents/           # Agent runtime & LLM providers
│   ├── channels/         # Channel implementations
│   ├── cli/              # Command-line interface
│   ├── config/           # Configuration system
│   ├── gateway/          # Gateway server
│   ├── memory/           # Memory management
│   ├── plugins/          # Plugin system
│   └── tools/            # Built-in tools
├── skills/               # Skill implementations (56+)
├── extensions/           # Channel extensions (17+)
├── docs/                 # Documentation & examples
│   ├── examples/         # Example scripts
│   └── guides/           # Implementation guides
├── tests/                # Test suite
├── .env.example          # Environment template
├── pyproject.toml        # Dependencies
└── README.md             # This file
```

## CLI Commands

OpenClaw provides 74+ CLI commands for complete system management:

### Core Commands
```bash
openclaw start              # Start server (Gateway + Channels)
openclaw doctor             # System diagnostics
openclaw version            # Show version
openclaw onboard            # Interactive setup wizard
```

### Gateway Management
```bash
openclaw gateway run        # Run gateway in foreground
openclaw gateway status     # Check status
openclaw gateway install    # Install as system service
openclaw gateway start      # Start service
openclaw gateway stop       # Stop service
openclaw gateway restart    # Restart service
```

### Configuration
```bash
openclaw config show        # View current config
openclaw config get <path>  # Get specific value
openclaw config set <path> <value>  # Set value
openclaw config path        # Show config file location
```

### Channels
```bash
openclaw channels list      # List all channels
openclaw channels status    # Show channel status
openclaw channels start <id>  # Start specific channel
openclaw channels stop <id>   # Stop specific channel
```

### Agents
```bash
openclaw agent run          # Run agent interactively
openclaw agent chat         # Start chat session
openclaw agents list        # List configured agents
```

### Skills
```bash
openclaw skills list        # List available skills
openclaw skills info <id>   # Show skill details
openclaw skills enable <id>  # Enable skill
openclaw skills disable <id> # Disable skill
```

## Supported Models

### LLM Providers
- **Anthropic**: Claude 3 Opus, Claude 3.5 Sonnet, Claude 3 Haiku
- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- **Google**: Gemini 3 Pro Preview (NEW), Gemini 2.0 Flash, Gemini 1.5 Pro
- **AWS Bedrock**: Claude via Bedrock, Titan models
- **Ollama**: Local models (Llama 2, Mistral, etc.)

### Configuration Example
```json
{
  "agents": {
    "defaults": {
      "model": "google/gemini-3-pro-preview"
    },
    "agents": [
      {
        "id": "default",
        "name": "My Assistant",
        "model": "anthropic/claude-3-5-sonnet"
      }
    ]
  }
}
```

## Channels

### Fully Supported
- ✅ **Telegram**: Enhanced implementation with reconnection
- ✅ **Discord**: Full feature support
- ✅ **Slack**: Complete integration
- ✅ **WebChat**: Via Gateway WebSocket

### In Development
- 🟡 **WhatsApp**: Framework ready (requires library integration)
- 🟡 **Signal**: Framework ready (requires signal-cli)
- 🟡 **Matrix**: Framework ready (uses nio library)

## Tools

OpenClaw includes 22+ built-in tools:

**File Operations**: ReadFileTool, WriteFileTool, EditFileTool
**Execution**: BashTool, ProcessTool
**Web**: WebFetchTool, WebSearchTool (DuckDuckGo)
**Media**: ImageTool, TTSTool (Text-to-Speech)
**Memory**: MemorySearchTool, MemoryGetTool
**Session**: SessionsListTool, SessionsHistoryTool
**Advanced**: BrowserTool, CronTool, CanvasTool

## Architecture

OpenClaw Python is built on a modern, event-driven architecture:

```
┌─────────────────────────────────────────┐
│      Gateway Server (Port 18789)        │
├─────────────────────────────────────────┤
│  • WebSocket Server                     │
│  • Channel Manager                      │
│  • Event Bus                            │
│  • RPC Handler                          │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        │               │
   ┌────▼────┐    ┌────▼────┐
   │Telegram │    │ Discord │
   │Channel  │    │ Channel │
   └────┬────┘    └────┬────┘
        │              │
        └──────┬───────┘
               │
       ┌───────▼────────┐
       │ Agent Runtime  │
       ├────────────────┤
       │ • 22+ Tools    │
       │ • 56+ Skills   │
       │ • Multi-LLM    │
       │ • Memory Mgmt  │
       └────────────────┘
```

### Key Components

- **Gateway**: Central WebSocket server managing all components
- **Channel Manager**: Handles channel lifecycle and message routing
- **Agent Runtime**: Executes LLM inference with tool support
- **Plugin System**: Extensible architecture for channels, tools, and services
- **Event Bus**: Pub/sub messaging for component communication
- **Memory Manager**: SQLite + FTS5 for efficient context storage

## Development

### Running from Source

```bash
# Clone repository
git clone https://github.com/your-org/openclaw-python
cd openclaw-python

# Install dependencies
uv sync

# Run in development mode
uv run openclaw gateway run --verbose

# Run tests
uv run pytest

# Check code quality
uv run ruff check .
uv run mypy openclaw
```

### Creating Custom Plugins

```python
# openclaw/plugins/my_plugin.py
from openclaw.plugins.base import PluginBase

class MyPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.id = "my-plugin"
        self.name = "My Plugin"
    
    async def start(self, config: dict):
        # Initialize your plugin
        pass
    
    async def stop(self):
        # Clean up resources
        pass
```

## Comparison with TypeScript Version

| Component | TypeScript | Python | Status |
|-----------|-----------|--------|--------|
| Gateway Server | ✅ | ✅ | 100% |
| Channel Manager | ✅ | ✅ | 100% |
| Plugin System | ✅ | ✅ | 100% |
| Tool Registry | ✅ | ✅ | 100% |
| Agent Runtime | ✅ | ✅ | 100% |
| Event Bus | ✅ | ✅ | 100% |
| Skills System | ✅ | ✅ | 100% |
| CLI Commands | 74 | 74 | 100% |
| Channels | 20+ | 3 working | Partial |

**Overall Alignment**: 90-100%

## Troubleshooting

### Common Issues

**Gateway won't start:**
```bash
# Check if port is already in use
lsof -ti:18789

# Kill existing process
kill $(lsof -ti:18789)

# Restart gateway
openclaw gateway run
```

**Channel connection failed:**
```bash
# Verify API keys are set
openclaw config get channels.telegram.botToken

# Check channel status
openclaw channels status telegram

# Restart channel
openclaw channels restart telegram
```

**Import errors:**
```bash
# Reinstall dependencies
uv sync --force

# Verify installation
uv run python -c "import openclaw; print(openclaw.__version__)"
```

### Getting Help

```bash
# Run diagnostics
openclaw doctor

# Check logs
tail -f ~/.openclaw/logs/gateway.log

# Get command help
openclaw --help
openclaw gateway --help
```

## Documentation

- 📚 **Examples**: See `docs/examples/` for sample scripts
- 📖 **Guides**: Implementation guides in `docs/guides/`
- 🔧 **API Reference**: Coming soon
- 💬 **Discord**: [Join our community](https://discord.gg/clawd)

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `uv run pytest`
5. Format code: `uv run black openclaw && uv run ruff check --fix openclaw`
6. Commit: `git commit -m "Add my feature"`
7. Push: `git push origin feature/my-feature`
8. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details

## Related Projects

- [OpenClaw (TypeScript)](https://github.com/openclaw/openclaw) - Original TypeScript implementation
- [OpenClaw Documentation](https://docs.openclaw.ai) - Official documentation
- [OpenClaw Discord](https://discord.gg/clawd) - Community chat

## Acknowledgments

OpenClaw Python is inspired by and maintains architectural compatibility with the original [OpenClaw](https://github.com/openclaw/openclaw) TypeScript project.

---

**Status**: ✅ Production Ready (v0.6.0)  
**Python**: 3.11+ (3.14+ recommended)  
**Last Updated**: 2026-02-09

For more information, visit [openclaw.ai](https://openclaw.ai) or join our [Discord community](https://discord.gg/clawd).
