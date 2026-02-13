# 🦞 OpenClaw Python

> **OpenClaw is great, but I also need Python!**  
> _A full-featured Python implementation of the OpenClaw AI assistant platform_

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**OpenClaw Python** is a complete Python port of OpenClaw, connecting messaging channels (Telegram, Discord, Slack) with AI models (Claude, GPT, Gemini). Built with Python's strengths for clarity and maintainability—because sometimes TypeScript just won't do, and Python's what you need to get through!

## ✨ Features

- 🤖 **Multi-Model Support**: Anthropic Claude, OpenAI GPT, Google Gemini, AWS Bedrock, Ollama
- 💬 **Multi-Channel**: Telegram, Discord, Slack, WebChat (extensible to WhatsApp, Signal, Matrix)
- ⏰ **Cron Scheduler**: Set reminders, recurring tasks ("wake me at 7am", "daily stock update")
- 🔧 **24+ Built-in Tools**: File ops, web search, bash, browser automation, memory search
- 🎓 **56+ Skills**: Modular extensions for specialized knowledge and workflows
- 🌐 **Web Control UI**: Browser-based interface for managing your assistant
- 🔐 **Security**: Comprehensive permission management and sandboxing

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (3.14+ recommended)
- **uv** package manager
- At least one LLM API key (Anthropic, OpenAI, or Google)

### Installation

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/your-org/openclaw-python
cd openclaw-python

# Install dependencies
uv sync
```

### Configuration

#### Option 1: Quick Setup (Recommended)

```bash
# Copy environment template
cp .env.example .env

# Edit and add your API keys
nano .env
```

Add at least one API key:
```bash
# Choose one or more providers
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here
GOOGLE_API_KEY=your-google-key-here

# Optional: Add channel tokens
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
DISCORD_BOT_TOKEN=your-discord-bot-token
```

#### Option 2: Interactive Wizard

```bash
# Run the setup wizard
uv run openclaw onboard
```

The wizard will guide you through:
- Security acknowledgement
- API key configuration
- Workspace setup
- Channel configuration
- Model selection

### Running

Start the gateway server:

```bash
# Quick start (foreground)
uv run openclaw start

# Or run gateway explicitly
uv run openclaw gateway run

# Install as system service
uv run openclaw gateway install
uv run openclaw gateway start
```

### Verify Installation

```bash
# Run system diagnostics
uv run openclaw doctor

# Check configuration
uv run openclaw config show

# List available channels
uv run openclaw channels list
```

### Web Control UI

Access the web interface at `http://localhost:8080` after starting the gateway.

The control UI provides:
- Real-time chat with your agent
- Channel status monitoring
- Configuration management
- Modern, responsive design

## 📖 Documentation

- **Quick Start**: You're reading it!
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: See [CHANGELOG.md](CHANGELOG.md)
- **API Reference**: Coming soon

## 🏗️ Project Structure

```
openclaw-python/
├── openclaw/           # Main package
│   ├── agents/        # Agent runtime & LLM providers
│   ├── channels/      # Channel implementations (Telegram, Discord, etc.)
│   ├── cli/           # Command-line interface (74+ commands)
│   ├── config/        # Configuration system
│   ├── gateway/       # Gateway server (WebSocket + HTTP)
│   ├── tools/         # Built-in tools (24+)
│   └── ...
├── skills/            # Skill implementations (56+)
├── tests/             # Test suite
├── .env.example       # Environment template
└── pyproject.toml     # Dependencies
```

## 🛠️ Key Commands

```bash
# Start/stop
openclaw start                    # Start server
openclaw gateway stop             # Stop gateway

# Configuration
openclaw config show              # View config
openclaw config set <key> <val>   # Update config

# Channels
openclaw channels list            # List channels
openclaw channels status          # Channel status

# Diagnostics
openclaw doctor                   # System health check
openclaw version                  # Show version
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Quick steps:
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and run tests: `uv run pytest`
4. Format code: `uv run ruff check --fix .`
5. Commit: `git commit -m "Add my feature"`
6. Push and open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Related Projects

- [OpenClaw (TypeScript)](https://github.com/openclaw/openclaw) - Original TypeScript implementation
- [OpenClaw Documentation](https://docs.openclaw.ai) - Official documentation
- [OpenClaw Discord](https://discord.gg/clawd) - Community chat

## 🙏 Acknowledgments

OpenClaw Python maintains architectural compatibility with the original [OpenClaw](https://github.com/openclaw/openclaw) TypeScript project.

---

**Status**: Production Ready (v0.6.0)  
**Python**: 3.11+ required, 3.14+ recommended  
**Last Updated**: 2026-02-13

For more information, visit [openclaw.ai](https://openclaw.ai)
