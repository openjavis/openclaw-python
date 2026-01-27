# ClawdBot Python

**Personal AI Assistant Platform - Complete Python Implementation**

This is a complete Python clone of [ClawdBot](https://github.com/badlogic/clawdbot), ported from TypeScript.

ClawdBot is a local-first AI assistant platform that connects to multiple messaging channels (WhatsApp, Telegram, Discord, Slack, etc.) and provides AI assistant services through these channels.

## About This Project

- **Original Project**: [ClawdBot (TypeScript)](https://github.com/badlogic/clawdbot)
- **Python Implementation**: Core features complete, actively catching up
- **Created**: 2026-01-27
- **Version**: 0.3.0
- **License**: MIT
- **Status**: 🚧 **~80-90% feature parity** - Core functionality complete and usable

### Implementation Progress

| Component | Status | Notes |
|-----------|--------|-------|
| **Agent Runtime** | ✅ Complete | Self-developed (not using Pi Agent), supports Claude + OpenAI |
| **Tools System** | ✅ 24 tools | Core tools implemented and tested |
| **Channel Plugins** | 🚧 17 channels | Framework ready, some need real API credentials testing |
| **Skills Library** | ✅ 52 skills | Ported from TypeScript version |
| **Gateway/API** | ✅ Complete | WebSocket server + HTTP API |
| **Documentation** | ✅ Complete | All docs translated to English |

**See [AGENT_IMPLEMENTATION.md](AGENT_IMPLEMENTATION.md) for details on our custom agent architecture.**

## Highlights (v0.3.0)

- ✅ **Self-Developed Agent** - Custom agent runtime (not Pi Agent), fully integrated
- ✅ **24 Tools** - Including Browser, Cron, TTS, Image, Memory, Patch, and channel actions
- 🚧 **17 Channels** - Framework implemented: Telegram, Discord, Slack, WhatsApp, Signal, Teams, LINE, iMessage, Matrix, Mattermost (some need API testing)
- ✅ **52 Skills** - Library ported: Notion, Obsidian, Spotify, Trello, 1Password, Apple Notes, Tmux, etc.
- ✅ **OpenAI-Compatible API** - `/v1/chat/completions` endpoint
- 🚧 **LanceDB Memory** - Vector search framework ready
- 🚧 **Playwright Automation** - Browser framework ready

## Features

- **Multi-Channel Support**: WhatsApp, Telegram, Discord, Slack, WebChat, and more
- **Local-First**: Runs on your hardware, keeps your data private
- **Gateway Architecture**: Single WebSocket control plane for all clients
- **Agent Runtime**: Streaming LLM responses with tool calling
- **58+ Skills**: Pre-built capabilities for common tasks
- **Plugin System**: Extensible architecture for custom channels and tools
- **Web UI**: Control panel and WebChat interface

## Quick Start

### Installation

```bash
# Install with poetry
poetry install

# Or with pip
pip install -e .
```

### Setup

```bash
# Run onboarding wizard
clawdbot onboard

# Start gateway
clawdbot gateway start
```

### Usage

```bash
# Run agent turn
clawdbot agent --message "Hello!"

# Manage channels
clawdbot channels list
clawdbot channels login telegram

# Check status
clawdbot status
```

## Architecture

```
Messaging Channels → Gateway (WebSocket) → Agent Runtime → LLM
                                ↓
                            CLI/Web UI
```

## Development

```bash
# Install dev dependencies
poetry install --with dev

# Run tests
pytest

# Format code
black clawdbot/
ruff check clawdbot/
```

## License

MIT License
