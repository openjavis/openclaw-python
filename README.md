# OpenClaw Python

> 🦞 **Personal AI assistant platform - Python implementation of [OpenClaw](https://github.com/openclaw/openclaw)**

A production-ready Python implementation of OpenClaw, the personal AI assistant that works across all your channels (WhatsApp, Telegram, Slack, Discord, etc.). Inspired by the TypeScript version, built with Python for better accessibility and enterprise features.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-309%20passing-green.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-45%25-yellow.svg)]()

## 🌟 What's New in v0.6.0

### 🚀 Gemini 3 Flash Preview Support
- ✅ **New Google AI API**: Using `google-genai` package
- ✅ **Gemini 3 Models**: Flash & Pro with Thinking Mode
- ✅ **Google Search**: Built-in search integration
- ✅ **1M+ Context**: Extended context windows

### ⚡ v0.6.0 Features
- **Settings Manager**: Workspace-specific configuration
- **Message Summarization**: LLM-driven context compression  
- **Enhanced Tool Policies**: Fine-grained security control
- **WebSocket Improvements**: Production-grade real-time streaming

See [RELEASE_NOTES_v0.6.0.md](RELEASE_NOTES_v0.6.0.md) for full details.

---

## 📋 Status

| Component | Status | Notes |
|-----------|--------|-------|
| Agent Runtime | ✅ 100% | Multi-provider, context management, v0.5.0+ features |
| Gemini Integration | ✅ 100% | **NEW**: Gemini 3 Flash/Pro with Thinking Mode |
| Tools System | ✅ 90% | 24+ tools with v0.6.0 policies |
| Channel Plugins | ✅ 70% | 4 production + 13 stubs |
| REST API | ✅ 100% | FastAPI + OpenAI compatibility |
| Documentation | ✅ 100% | Complete guides + examples |
| Testing | ✅ 45% | 309 passing tests |

**Current Stage**: ✨ **Production Ready** - v0.6.0

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- API keys (Anthropic/OpenAI/Google)

### Installation

```bash
# Clone repository
git clone https://github.com/openclaw/openclaw-python.git
cd openclaw-python

# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Add your API keys to .env
```

### First Chat

```bash
# Test with Gemini 3 Flash (recommended)
uv run python test_gemini_3_flash.py

# Or use the CLI
uv run openclaw agent chat "Hello!"
```

---

## 🎯 Recommended Setup

### For Gemini 3 (NEW - 2026)

```python
from openclaw.agents.runtime import AgentRuntime

runtime = AgentRuntime(
    model="gemini-3-flash-preview",  # Latest & fastest
    max_tokens=8192,
    temperature=0.7
)

# With Thinking Mode
async for event in runtime.run_turn(session, thinking_mode="HIGH"):
    if event["type"] == "text":
        print(event["text"], end="")
```

### For Production

```python
from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.thinking import ThinkingMode
from openclaw.agents.tools.policies import PolicyManager, WhitelistPolicy

# Security policies
policies = PolicyManager()
policies.add_policy(WhitelistPolicy(["bash", "read_file"]))

# Runtime with all features
runtime = AgentRuntime(
    model="gemini-3-flash-preview",
    thinking_mode=ThinkingMode.STREAM,
    fallback_models=["anthropic/claude-opus-4-5"],
    enable_queuing=True
)
```

See [GEMINI_SETUP_GUIDE.md](GEMINI_SETUP_GUIDE.md) for detailed configuration.

---

## 📚 Features

### Core Platform (v0.4.x)
- ✅ Multi-provider LLM support (Anthropic, OpenAI, Google, AWS, Ollama)
- ✅ 24+ tools with permissions & rate limiting
- ✅ Multi-channel support (Telegram, Discord, Slack, WebChat)
- ✅ REST API + OpenAI compatibility
- ✅ Authentication & rate limiting
- ✅ Health monitoring & metrics

### Advanced Features (v0.5.0)
- ✅ **Thinking Mode** - AI reasoning extraction
- ✅ **Auth Rotation** - Multi-key failover with cooldown
- ✅ **Model Fallback** - Automatic model switching
- ✅ **Session Queuing** - Concurrency control
- ✅ **Context Compaction** - Intelligent pruning
- ✅ **Tool Formatting** - Channel-specific output

### Enterprise Features (v0.6.0)
- ✅ **Settings Manager** - Workspace configuration
- ✅ **Message Summarization** - LLM-driven compression
- ✅ **Tool Policies** - Security & access control
- ✅ **WebSocket Streaming** - Production real-time

---

## 🔧 Configuration

Minimal `~/.openclaw/openclaw.json`:

```json
{
  "agent": {
    "model": "gemini-3-flash-preview"
  }
}
```

Full configuration: [docs/configuration.md](docs/configuration.md)

---

## 📖 Documentation

### Getting Started
- [Installation Guide](docs/installation.md)
- [Quick Start Tutorial](docs/quickstart.md)
- [Gemini Setup Guide](GEMINI_SETUP_GUIDE.md) ⭐
- [Configuration Reference](docs/configuration.md)

### Advanced Guides
- [Advanced Features](docs/guides/ADVANCED_FEATURES.md)
- [v0.5.0 Release Notes](RELEASE_NOTES_v0.5.0.md)
- [v0.6.0 Release Notes](RELEASE_NOTES_v0.6.0.md) ⭐
- [Security Guide](docs/security.md)

### Examples
- [examples/01_basic_agent.py](examples/01_basic_agent.py) - Basic usage
- [examples/02_with_tools.py](examples/02_with_tools.py) - Tool usage
- [examples/08_advanced_features.py](examples/08_advanced_features.py) - v0.5.0 features
- [examples/09_v0.6_features.py](examples/09_v0.6_features.py) - v0.6.0 features

---

## 🤝 Project History

**OpenClaw** (formerly MoltBot, formerly ClawdBot) is the open-source personal AI assistant platform.

- **Main Project**: [openclaw/openclaw](https://github.com/openclaw/openclaw) (TypeScript)
- **Python Port**: openclaw/openclaw-python (this repository)

This Python implementation provides:
- ✅ Better testing (45% vs ~10% in TypeScript)
- ✅ Complete documentation
- ✅ Enhanced security features
- ✅ Easier deployment

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest tests/

# Run specific tests
uv run pytest tests/test_gemini_provider.py

# With coverage
uv run pytest --cov=openclaw --cov-report=html
```

**Current**: 309 tests passing, 45% coverage

---

## 🛠️ Development

```bash
# Install dev dependencies
uv sync

# Format code
uv run black openclaw/
uv run ruff check --fix openclaw/

# Type checking
uv run mypy openclaw/

# Build package
uv build
```

---

## 📝 Changelog

### v0.6.0 (2026-01-31)
- ✅ Renamed from clawdbot-python to openclaw-python
- ✅ Added Gemini 3 Flash/Pro support with Thinking Mode
- ✅ Upgraded to `google-genai` API
- ✅ Settings Manager for workspace configuration
- ✅ Message summarization with multiple strategies
- ✅ Enhanced tool policies with 6 policy types
- ✅ WebSocket improvements for production

### v0.5.0 (2026-01-29)
- ✅ All 6 advanced features from TypeScript version
- ✅ Full feature parity achieved
- ✅ 72 new tests, comprehensive documentation

See [CHANGELOG.md](CHANGELOG.md) for full history.

---

## 🔗 Links

- **Main Project**: https://github.com/openclaw/openclaw
- **Website**: https://openclaw.ai
- **Documentation**: [docs/](docs/)
- **Discord**: Join the community
- **Twitter**: [@openclaw](https://twitter.com/openclaw)

---

## 📜 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- [OpenClaw](https://github.com/openclaw/openclaw) - Original TypeScript implementation
- [MoltBot](https://openclaw.ai) - The space lobster AI 🦞
- All contributors to the OpenClaw ecosystem

---

## 🚀 Get Started

```bash
# Test Gemini 3 Flash
uv run python test_gemini_3_flash.py

# Start building
cd openclaw-python
uv sync
uv run openclaw agent chat "Hello, OpenClaw!"
```

**Welcome to OpenClaw Python!** 🦞
