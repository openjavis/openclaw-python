#!/bin/bash

# OpenClaw 完整设置和启动脚本
# 自动检测环境并安装依赖

set -e

echo ""
echo "🦞 OpenClaw Python - 自动设置和启动"
echo "======================================"
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 步骤 1: 检查 Xcode Command Line Tools
echo "📋 步骤 1/5: 检查系统环境..."
if ! xcode-select -p &> /dev/null; then
    echo "❌ 未安装 Xcode Command Line Tools"
    echo ""
    echo "请先运行以下命令安装:"
    echo "  xcode-select --install"
    echo ""
    echo "安装完成后再次运行此脚本"
    exit 1
fi
echo "✅ 系统环境正常"

# 步骤 2: 检查配置文件
echo ""
echo "📋 步骤 2/5: 检查配置文件..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env 文件不存在，从模板创建..."
    cp .env.example .env
    echo "✅ .env 文件已创建"
fi

# 验证 API 密钥配置
echo ""
echo "🔑 验证 API 密钥配置..."
GOOGLE_KEY=$(grep "^GOOGLE_API_KEY=" .env | cut -d'=' -f2)
TELEGRAM_TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" .env | cut -d'=' -f2)

if [ -z "$GOOGLE_KEY" ] || [ "$GOOGLE_KEY" = "your-google-api-key" ]; then
    echo "⚠️  GOOGLE_API_KEY 未配置或使用默认值"
    echo "   请在 .env 文件中配置你的 Google API Key"
else
    echo "✅ Google API Key 已配置"
fi

if [ -z "$TELEGRAM_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN 未配置"
    echo "   请在 .env 文件中配置你的 Telegram Bot Token"
    exit 1
else
    echo "✅ Telegram Bot Token 已配置"
fi

# 步骤 3: 安装 uv
echo ""
echo "📋 步骤 3/5: 安装 uv 包管理器..."
if command -v uv &> /dev/null; then
    echo "✅ uv 已安装 ($(uv --version))"
else
    echo "⚙️  正在安装 uv..."
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        # 将 uv 添加到当前 shell 的 PATH
        export PATH="$HOME/.cargo/bin:$PATH"
        echo "✅ uv 安装成功"
    else
        echo "❌ uv 安装失败"
        echo "   请访问 https://docs.astral.sh/uv/ 查看安装说明"
        exit 1
    fi
fi

# 确保 uv 在 PATH 中
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

# 步骤 4: 同步项目依赖
echo ""
echo "📋 步骤 4/5: 同步项目依赖..."
echo "   (首次运行可能需要几分钟下载依赖)"
if uv sync; then
    echo "✅ 依赖同步完成"
else
    echo "❌ 依赖同步失败"
    exit 1
fi

# 步骤 5: 安装 Playwright 浏览器（可选）
echo ""
echo "📋 步骤 5/5: 安装 Playwright 浏览器..."
echo "   (可选步骤，用于浏览器自动化功能)"
if uv run python -m playwright install chromium 2>/dev/null; then
    echo "✅ Playwright 浏览器已安装"
else
    echo "⚠️  Playwright 浏览器安装失败（可选功能，不影响使用）"
fi

# 显示配置信息
echo ""
echo "======================================"
echo "✅ 设置完成！"
echo "======================================"
echo ""
echo "📊 配置信息:"
echo "   • 模型: gemini-3-flash-preview"
echo "   • Bot Token: ${TELEGRAM_TOKEN:0:20}..."
echo "   • API Key: ${GOOGLE_KEY:0:20}..."
echo ""
echo "======================================"
echo ""
echo "🚀 正在启动 Telegram Bot..."
echo ""
echo "📱 使用方法:"
echo "   1. 在 Telegram 中搜索你的 bot"
echo "   2. 点击 Start 或发送 /start"
echo "   3. 开始对话！"
echo ""
echo "💡 提示: 按 Ctrl+C 停止服务"
echo ""
echo "======================================"
echo ""

# 启动服务
uv run python examples/05_telegram_bot.py
