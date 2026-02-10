# Troubleshooting Guide

## Common Issues and Solutions

### 1. Port Already in Use Error

**Error Message:**
```
OSError: [Errno 48] error while attempting to bind on address ('127.0.0.1', 18789): 
[errno 48] address already in use
```

**Cause:** A previous instance of OpenClaw is still running on the port.

**Quick Fix:**
```bash
# Kill processes on OpenClaw ports
lsof -ti:18789 -ti:8080 | xargs kill -9

# Or find and kill manually
lsof -i:18789
lsof -i:8080
kill -9 <PID>
```

**Prevention:**
Always stop the gateway properly with `Ctrl+C` instead of force-closing the terminal.

---

### 2. No LLM API Key Found

**Error Message:**
```
❌ No LLM API key found
Cannot start without an LLM API key.
```

**Solution:**
Make sure your `.env` file has at least one API key:
```bash
# Edit .env file
nano .env

# Add one of these:
GOOGLE_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

---

### 3. Telegram Bot Token Not Set

**Error Message:**
```
⚠️  TELEGRAM_BOT_TOKEN not set
```

**Solution:**
Add your Telegram bot token to `.env`:
```bash
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

Or disable Telegram:
```bash
openclaw start --no-telegram
```

---

### 4. Module Import Error

**Error Message:**
```
ModuleNotFoundError: No module named 'xxx'
```

**Solution:**
Reinstall dependencies:
```bash
cd openclaw-python
uv sync
```

---

### 5. Gateway Handler Warning

**Warning Message:**
```
WARNING | Handler globals failed: 'GatewayBootstrap' object has no attribute 'gateway'
```

**Status:** This is a known harmless warning and doesn't affect functionality. It will be fixed in a future update.

---

### 6. WebSocket Connection Failed

**Issue:** Web UI can't connect to gateway

**Solution:**
1. Check gateway is running:
   ```bash
   lsof -i:18789
   ```

2. Check firewall settings

3. Restart gateway:
   ```bash
   openclaw gateway run
   ```

---

### 7. Config File Issues

**Error Message:**
```
Failed to load config from ~/.openclaw/openclaw.json
```

**Solution:**
1. Check config syntax:
   ```bash
   cat ~/.openclaw/openclaw.json
   ```

2. Reset config:
   ```bash
   rm ~/.openclaw/openclaw.json
   openclaw onboard
   ```

3. Or manually fix JSON syntax errors

---

## Quick Diagnostics

Run the doctor command to check system health:
```bash
openclaw doctor
```

For detailed diagnostics:
```bash
openclaw doctor --deep
```

Auto-fix common issues:
```bash
openclaw doctor --repair
```

---

## Getting Help

1. **Check logs:** Gateway logs show detailed error information
2. **GitHub Issues:** Report bugs at [your-repo-url]
3. **Documentation:** See README.md for full setup guide

---

## Debug Mode

For verbose logging:
```bash
# CLI
openclaw gateway run --verbose

# Or via start command
CLAWDBOT_LOG_LEVEL=DEBUG openclaw start
```
