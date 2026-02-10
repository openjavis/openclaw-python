#!/bin/bash
# OpenClaw Python 对话演示脚本

cd "$(dirname "$0")"

echo "🤖 OpenClaw Python 对话测试"
echo "=============================="
echo ""

# 检查 API key
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  警告: 未设置 API key"
    echo ""
    echo "请先设置至少一个 API key:"
    echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo "  export OPENAI_API_KEY='sk-...'"
    echo "  export GOOGLE_API_KEY='...'"
    echo ""
    echo "继续演示（将使用模拟响应）..."
    echo ""
fi

echo "1️⃣  基础对话测试"
echo "问题: '你好，介绍一下你自己'"
echo ""
/Users/openbot/.local/bin/uv run openclaw agent chat "你好，介绍一下你自己" 2>&1 || echo "需要设置 API key"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "2️⃣  代码生成测试"
echo "问题: '创建一个 Python 函数计算斐波那契数列'"
echo ""
/Users/openbot/.local/bin/uv run openclaw agent chat "创建一个简单的 Python 函数计算斐波那契数列" 2>&1 || echo "需要设置 API key"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "3️⃣  技能系统测试"
echo "查看所有可用技能..."
echo ""
/Users/openbot/.local/bin/uv run openclaw skills list --format table | head -15
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "4️⃣  工具系统测试"
echo "查看所有可用工具..."
echo ""
/Users/openbot/.local/bin/uv run openclaw tools list | head -15
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "✅ 演示完成！"
echo ""
echo "完整功能需要:"
echo "  1. 设置 API key"
echo "  2. 运行: openclaw gateway run"
echo "  3. 测试: openclaw agent chat '你的问题'"
