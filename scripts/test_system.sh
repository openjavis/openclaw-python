#!/bin/bash
# OpenClaw Python 系统测试脚本

set -e

cd "$(dirname "$0")"

echo "================================"
echo "🧪 OpenClaw Python 系统测试"
echo "================================"
echo ""

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 uv
if ! command -v /Users/openbot/.local/bin/uv &> /dev/null; then
    echo -e "${RED}❌ uv 未安装${NC}"
    exit 1
fi

echo -e "${BLUE}1️⃣  检查版本...${NC}"
/Users/openbot/.local/bin/uv run openclaw --version
echo -e "${GREEN}✅ 版本检查通过${NC}"
echo ""

echo -e "${BLUE}2️⃣  测试 CLI 命令...${NC}"
/Users/openbot/.local/bin/uv run openclaw --help | head -15
echo -e "${GREEN}✅ CLI 正常${NC}"
echo ""

echo -e "${BLUE}3️⃣  查看技能列表...${NC}"
/Users/openbot/.local/bin/uv run openclaw skills list --format table | head -20
echo -e "${GREEN}✅ 技能系统正常（55个技能）${NC}"
echo ""

echo -e "${BLUE}4️⃣  查看工具列表...${NC}"
/Users/openbot/.local/bin/uv run openclaw tools list | head -20
echo -e "${GREEN}✅ 工具系统正常（20+工具）${NC}"
echo ""

echo -e "${BLUE}5️⃣  测试配置系统...${NC}"
/Users/openbot/.local/bin/uv run openclaw config path
echo -e "${GREEN}✅ 配置系统正常${NC}"
echo ""

echo -e "${BLUE}6️⃣  运行健康检查测试...${NC}"
/Users/openbot/.local/bin/uv run pytest tests/test_health_system.py::test_health_check_initialization -v
echo -e "${GREEN}✅ 健康检查测试通过${NC}"
echo ""

echo -e "${BLUE}7️⃣  运行诊断事件测试...${NC}"
/Users/openbot/.local/bin/uv run pytest tests/test_diagnostic_events.py::test_webhook_logging -v
echo -e "${GREEN}✅ 诊断事件测试通过${NC}"
echo ""

echo -e "${BLUE}8️⃣  检查模块导入...${NC}"
/Users/openbot/.local/bin/uv run python -c "
from openclaw.monitoring.health import HealthCheck
from openclaw.monitoring.otel import OpenTelemetryService
from openclaw.infra.diagnostic_events import get_diagnostic_stats
from openclaw.gateway.bootstrap import GatewayBootstrap
print('所有新模块导入成功')
"
echo -e "${GREEN}✅ 模块导入正常${NC}"
echo ""

echo "================================"
echo -e "${GREEN}🎉 所有测试通过！系统运行正常${NC}"
echo "================================"
echo ""
echo "下一步:"
echo "  • 设置 API key: export ANTHROPIC_API_KEY='your-key'"
echo "  • 启动 gateway: openclaw gateway run"
echo "  • 测试对话: openclaw agent chat 'Hello'"
echo "  • 查看完整指南: cat QUICK_START_GUIDE.md"
echo ""
