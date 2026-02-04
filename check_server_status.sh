#!/bin/bash
# 检查 OpenClaw 服务器状态

echo "🔍 OpenClaw 服务器状态"
echo "==========================================="
echo ""

# 检查当前运行的服务
echo "📊 运行中的服务:"
echo ""

# 检查直接 Telegram Bot
if ps aux | grep -E "05_telegram_bot" | grep -v grep > /dev/null; then
    echo "✅ 直接 Telegram Bot (05) - 运行中"
    ps aux | grep -E "05_telegram_bot" | grep -v grep | awk '{print "   PID: " $2 " | CPU: " $3"% | Mem: " $4"%"}'
else
    echo "❌ 直接 Telegram Bot (05) - 未运行"
fi

echo ""

# 检查完整服务器
if ps aux | grep -E "10_gateway_telegram_bridge" | grep -v grep > /dev/null; then
    echo "✅ 完整服务器 (Gateway) - 运行中"
    ps aux | grep -E "10_gateway_telegram_bridge" | grep -v grep | awk '{print "   PID: " $2 " | CPU: " $3"% | Mem: " $4"%"}'
else
    echo "❌ 完整服务器 (Gateway) - 未运行"
fi

echo ""

# 检查 API 服务器
if ps aux | grep -E "openclaw api" | grep -v grep > /dev/null; then
    echo "✅ API 服务器 - 运行中"
    ps aux | grep -E "openclaw api" | grep -v grep | awk '{print "   PID: " $2 " | CPU: " $3"% | Mem: " $4"%"}'
else
    echo "❌ API 服务器 - 未运行"
fi

echo ""
echo "==========================================="
echo ""

# 检查端口
echo "🔌 端口状态:"
echo ""

# WebSocket Gateway 端口
if lsof -i :8765 2>/dev/null | grep LISTEN > /dev/null; then
    echo "✅ WebSocket Gateway (8765) - 监听中"
    lsof -i :8765 2>/dev/null | grep LISTEN | awk '{print "   PID: " $2 " | Process: " $1}'
else
    echo "❌ WebSocket Gateway (8765) - 未监听"
fi

# API 服务器端口
if lsof -i :18789 2>/dev/null | grep LISTEN > /dev/null; then
    echo "✅ API 服务器 (18789) - 监听中"
    lsof -i :18789 2>/dev/null | grep LISTEN | awk '{print "   PID: " $2 " | Process: " $1}'
else
    echo "❌ API 服务器 (18789) - 未监听"
fi

echo ""
echo "==========================================="
echo ""

# 日志文件
echo "📋 日志文件:"
echo ""

if [ -f "/tmp/telegram_bot.log" ]; then
    size=$(ls -lh /tmp/telegram_bot.log | awk '{print $5}')
    modified=$(ls -l /tmp/telegram_bot.log | awk '{print $6, $7, $8}')
    echo "  📄 Telegram Bot: /tmp/telegram_bot.log"
    echo "     大小: $size | 修改: $modified"
    echo "     最后 3 行:"
    tail -3 /tmp/telegram_bot.log 2>/dev/null | sed 's/^/     > /'
else
    echo "  ❌ Telegram Bot: 日志不存在"
fi

echo ""

if [ -f "/tmp/openclaw_server.log" ]; then
    size=$(ls -lh /tmp/openclaw_server.log | awk '{print $5}')
    modified=$(ls -l /tmp/openclaw_server.log | awk '{print $6, $7, $8}')
    echo "  📄 完整服务器: /tmp/openclaw_server.log"
    echo "     大小: $size | 修改: $modified"
    echo "     最后 3 行:"
    tail -3 /tmp/openclaw_server.log 2>/dev/null | sed 's/^/     > /'
else
    echo "  ❌ 完整服务器: 日志不存在"
fi

echo ""
echo "==========================================="
echo ""

# 快捷命令
echo "💡 快捷命令:"
echo ""
echo "  启动完整服务器:"
echo "    ./start_full_server.sh"
echo ""
echo "  启动简单 Bot:"
echo "    ./start_telegram_bot.sh"
echo ""
echo "  查看实时日志:"
echo "    tail -f /tmp/telegram_bot.log"
echo "    tail -f /tmp/openclaw_server.log"
echo ""
echo "  停止服务:"
echo "    pkill -f 05_telegram_bot         # 停止简单 Bot"
echo "    pkill -f 10_gateway_telegram     # 停止完整服务器"
echo ""
