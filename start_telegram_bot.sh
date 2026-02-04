#!/bin/bash

# OpenClaw Telegram Bot 启动脚本
# 使用 Gemini 3 Flash Preview 模型

set -e

echo "🦞 OpenClaw Telegram Bot 启动脚本"
echo "=================================="
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 检查环境配置
if [ ! -f ".env" ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "   请先复制 .env.example 到 .env 并配置API密钥"
    exit 1
fi

# 检查 GOOGLE_API_KEY
if ! grep -q "^GOOGLE_API_KEY=" .env || grep -q "^GOOGLE_API_KEY=your-google-api-key" .env || grep -q "^GOOGLE_API_KEY=$" .env; then
    echo "⚠️  警告: GOOGLE_API_KEY 未配置"
fi

# 检查 TELEGRAM_BOT_TOKEN
if ! grep -q "^TELEGRAM_BOT_TOKEN=" .env || grep -q "^TELEGRAM_BOT_TOKEN=$" .env; then
    echo "❌ 错误: TELEGRAM_BOT_TOKEN 未配置"
    echo "   请在 .env 文件中配置 Telegram Bot Token"
    exit 1
fi

echo "✅ 配置文件检查完成"
echo ""
echo "📦 检查依赖..."

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装，尝试安装..."
    
    # 检查是否有 Command Line Tools
    if ! command -v python3 &> /dev/null; then
        echo ""
        echo "❌ Python 环境未就绪"
        echo "   请先安装 Xcode Command Line Tools:"
        echo "   xcode-select --install"
        exit 1
    fi
    
    # 尝试使用 pip 安装 uv
    echo "使用 pip 安装 uv..."
    pip3 install --user uv || {
        echo "❌ uv 安装失败"
        echo "   请手动安装: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    }
    
    # 将 uv 添加到 PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

echo "✅ uv 已安装"
echo ""
echo "🔧 同步项目依赖..."

# 同步依赖
uv sync || {
    echo "❌ 依赖同步失败"
    exit 1
}

echo "✅ 依赖同步完成"
echo ""
echo "🚀 启动 Telegram Bot..."
echo "   模型: gemini-3-flash-preview"
echo ""
echo "📱 现在可以在 Telegram 中向你的 bot 发送消息了"
echo "   按 Ctrl+C 停止服务"
echo ""
echo "=================================="
echo ""

# 启动 bot
uv run python examples/05_telegram_bot.py
