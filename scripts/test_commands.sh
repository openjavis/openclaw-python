#!/bin/bash
# OpenClaw 命令测试脚本

cd "$(dirname "$0")"

echo "🧪 OpenClaw 命令测试"
echo "===================="
echo ""

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

# 检查 Gateway 是否运行
if ! lsof -i :18789 | grep -q LISTEN; then
    echo -e "${YELLOW}⚠️  Gateway 未运行${NC}"
    echo "请先启动 Gateway:"
    echo "  /Users/openbot/.local/bin/uv run openclaw gateway run"
    echo ""
fi

echo -e "${BLUE}1️⃣  测试 agent run 命令${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$ openclaw agent run -m '你好，介绍一下你自己'"
echo ""
/Users/openbot/.local/bin/uv run openclaw agent run -m "你好，介绍一下你自己"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}2️⃣  查看技能列表${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
/Users/openbot/.local/bin/uv run openclaw skills list | head -20
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}3️⃣  查看工具列表${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
/Users/openbot/.local/bin/uv run openclaw tools list | head -20
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}4️⃣  查看配置${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
/Users/openbot/.local/bin/uv run openclaw config path
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo -e "${BLUE}5️⃣  查看频道状态${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
/Users/openbot/.local/bin/uv run openclaw channels status
echo ""

echo -e "${GREEN}✅ 测试完成${NC}"
echo ""
echo "常用命令:"
echo "  • 对话: openclaw agent run -m '你的消息'"
echo "  • 技能: openclaw skills list"
echo "  • 工具: openclaw tools list"
echo "  • 状态: openclaw gateway status"
echo "  • 帮助: openclaw --help"
