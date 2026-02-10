#!/bin/bash
# OpenClaw Python 测试运行脚本

cd "$(dirname "$0")"

echo "🧪 OpenClaw Python 测试套件"
echo "=============================="
echo ""

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

# 使用 uv run python -m pytest
PYTEST="/Users/openbot/.local/bin/uv run python -m pytest"

# 选项
VERBOSE="-v"
MARKERS=""
COVERAGE=""

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            echo -e "${BLUE}运行单元测试...${NC}"
            MARKERS="-m unit"
            shift
            ;;
        --integration)
            echo -e "${BLUE}运行集成测试...${NC}"
            MARKERS="-m integration"
            shift
            ;;
        --cov)
            echo -e "${BLUE}生成覆盖率报告...${NC}"
            COVERAGE="--cov=openclaw --cov-report=term-missing"
            shift
            ;;
        --fast)
            echo -e "${BLUE}跳过慢速测试...${NC}"
            MARKERS="-m 'not slow'"
            shift
            ;;
        *)
            echo "未知选项: $1"
            shift
            ;;
    esac
done

# 运行测试
echo -e "${BLUE}执行测试...${NC}"
$PYTEST $VERBOSE $MARKERS $COVERAGE tests/

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
else
    echo ""
    echo -e "${RED}❌ 测试失败 (退出码: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE
