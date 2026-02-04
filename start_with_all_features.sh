#!/bin/bash

# OpenClaw Python - 启动完整功能服务器
# 包含: 所有Tools + 所有Skills + 完整Memory管理

set -e

echo ""
echo "🦞 OpenClaw Python - 完整功能启动"
echo "=================================================================="
echo ""

cd "$(dirname "$0")"

# 检查配置
if [ ! -f ".env" ]; then
    echo "❌ 错误: .env 文件不存在"
    exit 1
fi

# 确保 PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# 检查已运行的实例
if ps aux | grep -E "start_full_featured|10_gateway|05_telegram" | grep -v grep > /dev/null; then
    echo "⚠️  检测到已有服务在运行:"
    ps aux | grep -E "start_full_featured|10_gateway|05_telegram" | grep -v grep | awk '{print "   - PID " $2 ": " $11" "$12" "$13}'
    echo ""
    read -p "是否停止所有实例并重启？(y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo "   停止旧实例..."
        pkill -f "start_full_featured" 2>/dev/null || true
        pkill -f "10_gateway" 2>/dev/null || true
        pkill -f "05_telegram" 2>/dev/null || true
        sleep 2
        echo "   ✅ 已停止"
    else
        echo "   取消启动"
        exit 0
    fi
fi

echo "🚀 启动完整功能服务器..."
echo ""
echo "包含功能："
echo "  ✅ 24+ 内置工具 (Browser, Bash, File, Web, Image, etc.)"
echo "  ✅ 50+ 技能 (GitHub, Notion, Obsidian, Slack, etc.)"
echo "  ✅ 完整 Memory 管理 (自动保存、智能压缩)"
echo "  ✅ Context 自动管理 (无限对话历史)"
echo "  ✅ Gateway + WebSocket API (:8765)"
echo "  ✅ 多频道支持 (Telegram/Discord/Slack)"
echo "  ✅ Event Broadcasting (实时事件)"
echo ""
echo "=================================================================="
echo ""

# 选择运行方式
if [ "$1" = "bg" ] || [ "$1" = "background" ]; then
    # 后台运行
    echo "🔄 在后台启动..."
    nohup uv run python start_full_featured.py > /tmp/openclaw_full.log 2>&1 &
    pid=$!
    sleep 3
    
    if ps -p $pid > /dev/null; then
        echo "✅ 服务已在后台启动 (PID: $pid)"
        echo ""
        echo "查看日志:"
        echo "  tail -f /tmp/openclaw_full.log"
        echo ""
        echo "停止服务:"
        echo "  kill $pid"
        echo "  # 或"
        echo "  pkill -f start_full_featured"
    else
        echo "❌ 启动失败，查看日志:"
        echo "  tail -50 /tmp/openclaw_full.log"
    fi
else
    # 前台运行（默认）
    echo "🔄 启动服务（前台模式）..."
    echo ""
    echo "💡 提示："
    echo "   • 在 Telegram 中发送消息即可使用所有功能"
    echo "   • Agent 会自动使用合适的工具和技能"
    echo "   • 对话历史会自动保存和压缩"
    echo "   • 按 Ctrl+C 停止服务"
    echo ""
    uv run python start_full_featured.py
fi
