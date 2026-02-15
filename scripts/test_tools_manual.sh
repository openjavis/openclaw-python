#!/bin/bash
# Manual testing script for OpenClaw tools
# Run this and then test via Telegram

set -e

cd "$(dirname "$0")/.."

echo "=================================================="
echo "OpenClaw Manual Tool Testing Guide"
echo "=================================================="
echo ""
echo "This script will help you test OpenClaw tools manually."
echo "Follow the instructions below and test via Telegram."
echo ""

# Check if gateway is running
if pgrep -f "openclaw.*start" > /dev/null; then
    echo "✅ Gateway is running"
else
    echo "⚠️  Gateway is not running"
    echo "   Starting gateway..."
    uv run openclaw gateway restart
    sleep 3
fi

echo ""
echo "=================================================="
echo "Manual Test Checklist (send to Telegram bot)"
echo "=================================================="
echo ""

echo "1️⃣  Test Bash Tool"
echo "   Message: 今天是哪天"
echo "   Expected: Should return current date"
echo ""
read -p "Press Enter after testing bash tool..."

echo ""
echo "2️⃣  Test Web Search Tool"
echo "   Message: 财经新闻"
echo "   Expected: Should return financial news search results"
echo ""
read -p "Press Enter after testing web search..."

echo ""
echo "3️⃣  Test PPT Generation"
echo "   Message: 做个ppt发过来，关于Python编程"
echo "   Expected: Should generate and send a PPT file"
echo ""
read -p "Press Enter after testing PPT generation..."

echo ""
echo "4️⃣  Test PDF Generation"
echo "   Message: 生成一个 PDF 文件关于人工智能"
echo "   Expected: Should generate and send a PDF file"
echo ""
read -p "Press Enter after testing PDF generation..."

echo ""
echo "5️⃣  Test Image Search"
echo "   Message: 网上找几张春节的图片"
echo "   Expected: Should return image links or descriptions"
echo ""
read -p "Press Enter after testing image search..."

echo ""
echo "6️⃣  Test Cron - Add Job"
echo "   Message: 每天早上9点提醒我吃早餐"
echo "   Expected: Should create a cron job"
echo ""
read -p "Press Enter after testing cron add..."

echo ""
echo "7️⃣  Test Cron - List Jobs"
echo "   Message: 列出所有定时任务"
echo "   Expected: Should show list of cron jobs"
echo ""
read -p "Press Enter after testing cron list..."

echo ""
echo "8️⃣  Test Cron - Remove Job"
echo "   Message: 删除定时任务 [job-id from previous step]"
echo "   Expected: Should remove the cron job"
echo ""
read -p "Press Enter after testing cron remove..."

echo ""
echo "=================================================="
echo "Error Handling Tests"
echo "=================================================="
echo ""

echo "9️⃣  Test Invalid Command"
echo "   Message: foobar123invalid"
echo "   Expected: Should handle gracefully with error message"
echo ""
read -p "Press Enter after testing invalid command..."

echo ""
echo "🔟 Test Long Conversation"
echo "   Have a multi-turn conversation (5+ messages)"
echo "   Expected: Context should be maintained"
echo ""
read -p "Press Enter after testing long conversation..."

echo ""
echo "=================================================="
echo "Test Complete!"
echo "=================================================="
echo ""
echo "Check logs for any errors:"
echo "  tail -f ~/.openclaw/logs/gateway.out.log"
echo ""
echo "If all tests passed, the agent is working correctly! ✅"
