# Quick Fix - Command Not Found Issues

## Problem
```bash
zsh: command not found: uv
zsh: command not found: openclaw
```

## Solution

### Step 1: Add uv to PATH

**Option A: Temporary (current session only)**
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Option B: Permanent (recommended)**

Add to your `~/.zshrc`:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Verify uv is working
```bash
uv --version
# Should show: uv 0.10.0 (or similar)
```

### Step 3: Install dependencies
```bash
cd openclaw-python
uv sync
```

### Step 4: Run openclaw commands

**Two ways to run openclaw:**

**Method 1: Using `uv run` (recommended)**
```bash
uv run openclaw onboard
uv run openclaw doctor
uv run openclaw gateway run
```

**Method 2: Activate virtual environment first**
```bash
source .venv/bin/activate
openclaw onboard
openclaw doctor
openclaw gateway run
```

## Complete Setup Sequence

```bash
# 1. Add uv to PATH (permanent)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# 2. Navigate to project
cd ~/Desktop/xopen/openclaw-python

# 3. Install dependencies
uv sync

# 4. Run onboarding
uv run openclaw onboard

# 5. Start the system
uv run openclaw start
```

## Quick Commands Reference

```bash
# Check system health
uv run openclaw doctor

# Show configuration
uv run openclaw config show

# Run gateway
uv run openclaw gateway run --verbose

# List channels
uv run openclaw channels list

# Show version
uv run openclaw version
```

## Alternative: Create Shell Alias

Add to `~/.zshrc` for convenience:
```bash
alias openclaw='uv run openclaw'
```

Then reload:
```bash
source ~/.zshrc
```

Now you can use:
```bash
openclaw onboard
openclaw start
openclaw doctor
```

## Troubleshooting

**If `uv sync` fails:**
```bash
# Check Python version
python3 --version  # Should be 3.11+

# Try with verbose output
uv sync --verbose
```

**If PATH doesn't persist:**
```bash
# Check which shell you're using
echo $SHELL

# For bash, use ~/.bashrc instead
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**If commands still don't work:**
```bash
# Check if virtual environment was created
ls -la .venv/

# Manually activate venv
source .venv/bin/activate

# Now openclaw should work directly
openclaw --help
```

## Expected Output After Setup

```bash
$ uv --version
uv 0.10.0 (0ba432459 2026-02-05)

$ uv run openclaw version
OpenClaw Python v0.6.0

$ uv run openclaw doctor
Running diagnostics...

✓ Python 3.14.3
✓ Config file: ~/.openclaw/openclaw.json
✓ Config file is valid
✓ Workspace: ~/.openclaw
✓ anthropic package installed

✓ All checks passed!
```

---

**Status**: Ready to use! 🚀
