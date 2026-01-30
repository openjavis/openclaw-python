# Quick Start Guide

Get ClawdBot Python up and running in minutes.

## Prerequisites

- Python 3.11+
- pip or Poetry
- API keys (Anthropic or OpenAI)

## Installation

### Option 1: Poetry (Recommended)

```bash
cd openclaw-python
poetry install
```

### Option 2: pip

```bash
cd openclaw-python
pip install -e .
```

### Optional Dependencies

For full functionality:

```bash
# Search and memory
pip install duckduckgo-search sentence-transformers torch pyarrow lancedb

# Browser automation
pip install playwright
playwright install

# Scheduler
pip install apscheduler

# Additional channels
pip install line-bot-sdk mattermostdriver matrix-nio

# Voice and media
pip install elevenlabs twilio psutil pillow
```

## Configuration

### 1. Run Onboarding

```bash
openclaw onboard
```

This creates `~/.openclaw/openclaw.json` with default configuration.

### 2. Set API Keys

```bash
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
```

### 3. Configure Channels (Optional)

Edit `~/.openclaw/openclaw.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "your-bot-token"
    },
    "discord": {
      "enabled": true,
      "botToken": "your-bot-token"
    }
  }
}
```

## Usage

### Start Gateway

```bash
openclaw gateway start
```

The gateway listens on WebSocket port 18789.

### Run Agent

```bash
# Interactive mode
openclaw agent run

# Single turn
openclaw agent run "What's the weather today?"

# With specific model
openclaw agent run --model claude-opus-4 "Help me code"
```

### Channel Management

```bash
# List channels
openclaw channels list

# Login to channel
openclaw channels login telegram
openclaw channels login discord
```

### Web UI

```bash
# Start web server
uvicorn openclaw.web.app:app --reload --port 8080
```

Then visit http://localhost:8080

## Testing

```bash
# Run tests
pytest

# Check status
openclaw status

# Run doctor
openclaw doctor
```

## Common Commands

```bash
# Status check
openclaw status

# Health check
openclaw doctor

# List sessions
openclaw agent sessions

# Clear sessions
rm -rf ~/.openclaw/sessions/*
```

## Next Steps

1. Read [CONTRIBUTING.md](CONTRIBUTING.md) for development
2. Check [skills/](skills/) for available skills
3. Explore [extensions/](extensions/) for plugins
4. See [FEATURES_COMPLETE.md](FEATURES_COMPLETE.md) for full feature list

## Troubleshooting

### Gateway won't start
- Check port 18789 is available
- Verify config file exists: `~/.openclaw/openclaw.json`

### API errors
- Verify API keys are set
- Check API key validity
- Check internet connection

### Channel errors
- Verify bot tokens
- Check channel-specific requirements
- See channel documentation in `openclaw/channels/`

## Support

For issues or questions, check:
- GitHub Issues
- Documentation in `docs/`
- Original ClawdBot project

## License

MIT License
