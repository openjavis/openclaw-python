#!/bin/bash
# OpenClaw Python - Environment Setup Script
# This script adds uv to PATH and sets up the environment

set -e  # Exit on error

echo "🦞 OpenClaw Python - Environment Setup"
echo "========================================"
echo ""

# Check if uv is installed
if [ ! -f "$HOME/.local/bin/uv" ]; then
    echo "❌ Error: uv is not installed at ~/.local/bin/uv"
    echo "   Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✓ Found uv at ~/.local/bin/uv"

# Detect shell
SHELL_NAME=$(basename "$SHELL")
echo "✓ Detected shell: $SHELL_NAME"

# Determine shell config file
if [ "$SHELL_NAME" = "zsh" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ]; then
    SHELL_RC="$HOME/.bashrc"
else
    echo "⚠️  Warning: Unknown shell ($SHELL_NAME)"
    echo "   Defaulting to ~/.zshrc"
    SHELL_RC="$HOME/.zshrc"
fi

# Check if PATH is already set
if grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$SHELL_RC" 2>/dev/null; then
    echo "✓ PATH already configured in $SHELL_RC"
else
    echo "📝 Adding PATH to $SHELL_RC"
    echo '' >> "$SHELL_RC"
    echo '# OpenClaw Python - uv path' >> "$SHELL_RC"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "✓ PATH added to $SHELL_RC"
fi

# Add convenient alias
if grep -q "alias openclaw=" "$SHELL_RC" 2>/dev/null; then
    echo "✓ openclaw alias already configured"
else
    echo "📝 Adding openclaw alias to $SHELL_RC"
    echo "alias openclaw='uv run openclaw'" >> "$SHELL_RC"
    echo "✓ Alias added to $SHELL_RC"
fi

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Reload your shell configuration:"
echo "   source $SHELL_RC"
echo ""
echo "2. Install project dependencies:"
echo "   cd ~/Desktop/xopen/openclaw-python"
echo "   uv sync"
echo ""
echo "3. Run onboarding wizard:"
echo "   openclaw onboard"
echo ""
echo "4. Start the system:"
echo "   openclaw start"
echo ""
echo "Or run all steps now:"
echo "   source $SHELL_RC && cd ~/Desktop/xopen/openclaw-python && uv sync && openclaw onboard"
echo ""
