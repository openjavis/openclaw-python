#!/bin/bash
# Quick restart script for OpenClaw Python

echo "🔄 Restarting OpenClaw..."

# Kill existing processes
echo "📍 Killing existing processes..."
lsof -ti:18789 -ti:8080 | xargs kill -9 2>/dev/null
sleep 2

# Clear cache
echo "🗑️  Clearing Python cache..."
find openclaw -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Check configuration
echo "⚙️  Configuration:"
echo "  Model: $(cat ~/.openclaw/openclaw.json | grep '"model"' | head -1 | awk -F'"' '{print $4}')"
echo "  API Keys:"
if [ -n "$GOOGLE_API_KEY" ]; then
    echo "    ✅ GOOGLE_API_KEY set"
else
    echo "    ❌ GOOGLE_API_KEY missing"
fi
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "    ✅ TELEGRAM_BOT_TOKEN set"
else
    echo "    ⚠️  TELEGRAM_BOT_TOKEN missing"
fi

echo ""
echo "🚀 Starting OpenClaw..."
echo "   Press Ctrl+C to stop"
echo ""

# Start
uv run openclaw start
