#!/bin/bash

# OpenClaw 完整服务器启动脚本
# Gateway + Channel Manager + WebSocket API

set -e

echo ""
echo "🦞 OpenClaw Python - 完整服务器启动"
echo "==========================================="
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 检查配置
if [ ! -f ".env" ]; then
    echo "❌ 错误: .env 文件不存在"
    exit 1
fi

# 验证 API Key
if ! grep -q "^GOOGLE_API_KEY=" .env || grep -q "^GOOGLE_API_KEY=$" .env; then
    echo "⚠️  警告: GOOGLE_API_KEY 未配置"
fi

# 验证 Telegram Token
if ! grep -q "^TELEGRAM_BOT_TOKEN=" .env || grep -q "^TELEGRAM_BOT_TOKEN=$" .env; then
    echo "⚠️  警告: TELEGRAM_BOT_TOKEN 未配置"
    echo "   Gateway 将启动，但 Telegram 频道将被禁用"
fi

echo "✅ 配置检查完成"
echo ""

# 确保 PATH 包含 uv
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# 检查是否已有实例在运行
if ps aux | grep -E "10_gateway_telegram_bridge" | grep -v grep > /dev/null; then
    echo "⚠️  检测到已有服务器在运行"
    read -p "   是否停止旧实例并重启？(y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        echo "   停止旧实例..."
        pkill -f "10_gateway_telegram_bridge" || true
        sleep 2
    else
        echo "   取消启动"
        exit 0
    fi
fi

echo "🚀 启动 OpenClaw 完整服务器..."
echo ""
echo "功能："
echo "  ✅ Gateway Server"
echo "  ✅ Channel Manager (Telegram/Discord/...)"
echo "  ✅ WebSocket API (ws://localhost:8765)"
echo "  ✅ Event Broadcasting"
echo "  ✅ Agent Runtime (Gemini 3 Flash)"
echo ""
echo "架构："
echo "  ┌─────────────────────────────────┐"
echo "  │      Gateway Server             │"
echo "  │  ├─ Channel Manager             │"
echo "  │  ├─ WebSocket API (:8765)       │"
echo "  │  ├─ Event Broadcasting          │"
echo "  │  └─ Agent Runtime               │"
echo "  └─────────────────────────────────┘"
echo ""
echo "==========================================="
echo ""
echo "💡 提示:"
echo "  - 查看日志: tail -f /tmp/openclaw_server.log"
echo "  - 停止服务: pkill -f 10_gateway_telegram_bridge"
echo "  - WebSocket: ws://localhost:8765"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 选择运行方式
if [ "$1" = "bg" ] || [ "$1" = "background" ]; then
    # 后台运行
    echo "🔄 在后台启动服务..."
    nohup uv run python examples/10_gateway_telegram_bridge.py > /tmp/openclaw_server.log 2>&1 &
    pid=$!
    echo "✅ 服务已在后台启动 (PID: $pid)"
    echo ""
    echo "查看日志:"
    echo "  tail -f /tmp/openclaw_server.log"
else
    # 前台运行（默认）
    echo "🔄 启动服务（前台模式）..."
    echo ""
    uv run python examples/10_gateway_telegram_bridge.py
fi
