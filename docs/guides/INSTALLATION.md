# Installation Guide

Complete installation guide for ClawdBot Python v0.3.0

---

## System Requirements

- **OS**: Linux, macOS, or Windows
- **Python**: 3.11 or higher
- **Memory**: 2GB+ RAM recommended
- **Disk**: 500MB free space

---

## Installation Methods

### Method 1: Poetry (Recommended)

```bash
# Install Poetry if not installed
curl -sSL https://install.python-poetry.org | python3 -

# Install ClawdBot
cd openclaw-python
poetry install

# Activate environment
poetry shell
```

### Method 2: pip

```bash
cd openclaw-python
pip install -e .
```

### Method 3: pip with all features

```bash
cd openclaw-python
pip install -e ".[all]"
```

---

## Dependencies

### Core Dependencies (Auto-installed)

- fastapi, uvicorn, websockets
- pydantic, pydantic-settings
- typer, rich
- anthropic, openai
- python-telegram-bot, discord.py, slack-sdk
- httpx, aiofiles, pyyaml

### Optional Dependencies

#### Search and Memory
```bash
pip install duckduckgo-search sentence-transformers torch pyarrow lancedb
```

#### Browser Automation
```bash
pip install playwright
playwright install  # Install browsers
```

#### Advanced Features
```bash
pip install apscheduler psutil pillow
```

#### Voice Features
```bash
pip install elevenlabs twilio
```

#### Additional Channels
```bash
pip install line-bot-sdk mattermostdriver matrix-nio
pip install google-cloud-pubsub google-auth
```

---

## Configuration

### 1. Run Onboarding

```bash
openclaw onboard
```

Creates `~/.openclaw/openclaw.json` with default config.

### 2. Set API Keys

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

Or add to `~/.bashrc` / `~/.zshrc`:
```bash
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc
```

### 3. Configure Channels

Edit `~/.openclaw/openclaw.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "botToken": "123456:ABC-DEF..."
    },
    "discord": {
      "enabled": true,
      "botToken": "MTA..."
    },
    "slack": {
      "enabled": true,
      "botToken": "xoxb-..."
    }
  }
}
```

---

## Verification

### Check Installation

```bash
openclaw --version
# Should show: 0.3.0

openclaw doctor
# Verifies installation and config
```

### Verify Features

```bash
./verify_features.sh
# Should show 100% completion
```

---

## Platform-Specific Setup

### macOS

```bash
# For iMessage support
# (osascript is built-in)

# For other features
brew install python@3.11
```

### Linux

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3.11 python3-pip

# For Signal support
# Install signal-cli separately
```

### Windows

```bash
# Use Python from python.org or Microsoft Store
# Some features may have limited support
```

---

## Troubleshooting

### Import Errors

```bash
# Reinstall dependencies
pip install -e . --force-reinstall
```

### API Key Errors

```bash
# Verify keys are set
echo $ANTHROPIC_API_KEY

# Test API
python -c "from anthropic import Anthropic; print(Anthropic().models.list())"
```

### Channel Errors

Check channel-specific requirements:
- Telegram: Bot token from @BotFather
- Discord: Bot token from Discord Developer Portal
- Slack: Bot token from api.slack.com

### Playwright Issues

```bash
# Reinstall browsers
playwright install chromium
```

---

## Next Steps

1. Read [QUICKSTART.md](QUICKSTART.md)
2. Configure channels you need
3. Start gateway: `openclaw gateway start`
4. Test: `openclaw agent run "Hello!"`

---

## Support

- Documentation: Check all .md files
- Issues: GitHub Issues
- Examples: See skills/ directory

**Installation Complete!** ✅
