# API Key Configuration Fixes

**Date**: February 10, 2026

## Problems Fixed

### 1. ❌ Model Mismatch Error
**Error**: `ANTHROPIC_API_KEY not provided` when `GOOGLE_API_KEY` is set

**Root Cause**:
- Default model in schema was hardcoded to `anthropic/claude-opus-4-5-20250514`
- Config file had different model
- System couldn't find matching API key

**Solution**:
- ✅ Changed default model to `google/gemini-3-pro-preview`
- ✅ Updated `openclaw.json` to use Gemini 3 Pro
- ✅ System now matches API key with configured model

### 2. ❌ Onboard Crash: 'NoneType' has no attribute 'model'
**Error**: During onboard step 7 (Saving Configuration)

**Root Cause**:
- `config.agents.defaults` was `None` by default
- Code tried to set `config.agents.defaults.model = model`
- Caused AttributeError

**Solution**:
- ✅ Changed `AgentsConfig.defaults` from `Optional` to always initialized
- ✅ Uses `default_factory=AgentDefaults` to create instance automatically
- ✅ Now `defaults` is never None

### 3. ❌ API Key Detection Logic
**Problem**: Didn't check environment before prompting user

**Solution**:
- ✅ Enhanced onboard to check environment variables first
- ✅ Asks user if they want to use existing key
- ✅ Only prompts for new key if needed
- ✅ Better user experience

## How API Keys Work Now

### Priority Order:
1. **Environment Variables** (`.env` file)
   - `GOOGLE_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `OPENAI_API_KEY`
   
2. **Model Configuration** (`openclaw.json`)
   - `agents.defaults.model` - sets which model to use
   - System automatically looks for matching API key

### Example Flow:

```bash
# You have GOOGLE_API_KEY in .env
GOOGLE_API_KEY=your-key-here

# Config uses Gemini model
{
  "agents": {
    "defaults": {
      "model": "google/gemini-3-pro-preview"
    }
  }
}

# ✅ System finds GOOGLE_API_KEY and works!
```

## Usage Guide

### Option 1: Use .env File (Recommended)

```bash
# Edit .env
nano .env

# Add your API key
GOOGLE_API_KEY=your-key-here
TELEGRAM_BOT_TOKEN=your-bot-token

# Start directly
openclaw start
```

### Option 2: Use Onboard Wizard

```bash
# Run wizard
openclaw onboard

# If API key found in environment:
# ✓ Found GOOGLE_API_KEY in environment
# Use existing GOOGLE_API_KEY? [Y/n]: y

# If NOT found, wizard will prompt:
# Enter your Google API key: [your-key]
# Save API key to .env file? [Y/n]: y
```

### Option 3: Manual Configuration

Edit `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "model": "google/gemini-3-pro-preview"
    }
  }
}
```

Then ensure matching API key in `.env`:
```bash
GOOGLE_API_KEY=your-key-here
```

## Supported Models & API Keys

| Provider | Model | Environment Variable |
|----------|-------|---------------------|
| Google Gemini | `google/gemini-3-pro-preview` | `GOOGLE_API_KEY` |
| Google Gemini | `google/gemini-2.0-flash-exp` | `GOOGLE_API_KEY` |
| Google Gemini | `google/gemini-1.5-pro` | `GOOGLE_API_KEY` |
| Anthropic | `anthropic/claude-opus-4-5-20250514` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |
| Groq | `groq/llama-3-70b-8192` | `GROQ_API_KEY` |
| Ollama | `ollama/llama3` | (Local, no key needed) |

## Testing Your Setup

```bash
# 1. Check configuration
openclaw doctor

# 2. Verify model and API key match
cat ~/.openclaw/openclaw.json | grep model
env | grep API_KEY

# 3. Test with a message
openclaw start
# Send "hello" to your Telegram bot
```

## Files Changed

1. `openclaw/config/schema.py`
   - Default model: `anthropic` → `google/gemini-3-pro-preview`
   - `AgentsConfig.defaults`: `Optional` → `default_factory`

2. `openclaw/wizard/onboarding.py`
   - Enhanced API key detection
   - Better environment variable handling

3. `~/.openclaw/openclaw.json`
   - Updated to use Gemini 3 Pro model
   - Added web UI configuration

## Quick Fix Commands

```bash
# If you get "ANTHROPIC_API_KEY not provided"
# Check your config model
cat ~/.openclaw/openclaw.json | grep model

# Should be: "model": "google/gemini-3-pro-preview"
# If not, run:
openclaw onboard

# Or manually edit ~/.openclaw/openclaw.json
```

## Summary

✅ **Model now defaults to Gemini 3 Pro** (matches most users' GOOGLE_API_KEY)  
✅ **Onboard wizard won't crash** (defaults always initialized)  
✅ **Smart API key detection** (checks environment first)  
✅ **Clear error messages** (tells you which key is missing)  

🚀 **Ready to use!** Just run `openclaw start`
