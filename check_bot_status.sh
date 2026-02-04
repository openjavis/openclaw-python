#!/bin/bash
# 检查 Telegram Bot 状态的快捷脚本

echo "🔍 Telegram Bot 状态检查"
echo "=================================="
echo ""

# 检查进程
echo "📊 进程状态:"
if ps aux | grep -E "telegram_bot|python.*05" | grep -v grep > /dev/null; then
    ps aux | grep -E "telegram_bot|python.*05" | grep -v grep | head -3
    echo "✅ Bot 正在运行"
else
    echo "❌ Bot 未运行"
fi

echo ""
echo "📋 最近日志 (最后20行):"
echo "=================================="
tail -20 /tmp/telegram_bot.log 2>/dev/null || echo "日志文件不存在"

echo ""
echo "=================================="
echo "💡 提示:"
echo "  - 查看实时日志: tail -f /tmp/telegram_bot.log"
echo "  - 停止服务: pkill -f 05_telegram_bot"
echo "  - 重启服务: cd /Users/openbot/Desktop/openclaw-python && ./start_telegram_bot.sh"
