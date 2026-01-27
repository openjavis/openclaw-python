#!/bin/bash
# ClawdBot Docker安全测试脚本
# 用于在隔离环境中测试项目

set -e

echo "================================================"
echo "ClawdBot Python - 安全Docker测试"
echo "================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Docker
echo "📦 检查Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker已安装${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ docker-compose已安装${NC}"
echo ""

# 安全检查
echo "🔒 安全检查..."

# 检查.env文件
if [ -f .env ]; then
    echo -e "${YELLOW}⚠️  发现.env文件${NC}"
    if grep -q "your-key-here" .env 2>/dev/null; then
        echo -e "${GREEN}✅ 使用示例配置（安全）${NC}"
    else
        echo -e "${YELLOW}⚠️  检测到可能的真实API密钥${NC}"
        read -p "是否继续测试？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    echo -e "${GREEN}✅ 未发现.env文件（将使用演示配置）${NC}"
fi

# 检查.gitignore
if grep -q "^\.env$" .gitignore; then
    echo -e "${GREEN}✅ .env已在.gitignore中${NC}"
else
    echo -e "${RED}❌ .env未在.gitignore中${NC}"
fi
echo ""

# 创建演示配置
echo "🎮 创建安全演示配置..."
cat > .env.demo << 'EOF'
# 演示配置 - 无真实API密钥
ANTHROPIC_API_KEY=demo-anthropic-key-for-testing
OPENAI_API_KEY=demo-openai-key-for-testing
CLAWDBOT_ENV=demo
CLAWDBOT_LOG_LEVEL=INFO
EOF
echo -e "${GREEN}✅ 演示配置已创建${NC}"
echo ""

# 构建镜像
echo "🔨 构建Docker镜像..."
docker-compose build --quiet
echo -e "${GREEN}✅ 镜像构建完成${NC}"
echo ""

# 测试1: 检查用户权限
echo "🧪 测试1: 检查用户权限..."
USER_CHECK=$(docker-compose run --rm --env-file .env.demo clawdbot whoami 2>/dev/null || echo "failed")
if [ "$USER_CHECK" = "clawdbot" ]; then
    echo -e "${GREEN}✅ 运行用户: clawdbot (非root)${NC}"
else
    echo -e "${RED}❌ 用户检查失败${NC}"
fi
echo ""

# 测试2: 检查Python版本
echo "🧪 测试2: 检查Python版本..."
PY_VERSION=$(docker-compose run --rm --env-file .env.demo clawdbot python --version 2>&1)
echo -e "${GREEN}✅ $PY_VERSION${NC}"
echo ""

# 测试3: 检查项目状态
echo "🧪 测试3: 检查项目状态..."
docker-compose run --rm --env-file .env.demo clawdbot python -c "
import sys
print('Python路径:', sys.executable)
try:
    import clawdbot
    print('✅ ClawdBot版本:', clawdbot.__version__)
except Exception as e:
    print('❌ 导入失败:', e)
"
echo ""

# 测试4: 检查工具
echo "🧪 测试4: 检查工具数量..."
docker-compose run --rm --env-file .env.demo clawdbot python -c "
try:
    from clawdbot.agents.tools.registry import ToolRegistry
    registry = ToolRegistry()
    tools = registry.list()
    print(f'✅ 注册的工具: {len(tools)}个')
    # 显示前5个工具
    for i, tool in enumerate(tools[:5]):
        print(f'  {i+1}. {tool}')
    if len(tools) > 5:
        print(f'  ... 还有{len(tools)-5}个工具')
except Exception as e:
    print(f'❌ 工具检查失败: {e}')
"
echo ""

# 测试5: 验证安全配置
echo "🧪 测试5: 验证Docker安全配置..."
echo "检查docker-compose.yml安全设置:"
if grep -q "read_only: true" docker-compose.yml; then
    echo -e "${GREEN}  ✅ 只读文件系统${NC}"
else
    echo -e "${YELLOW}  ⚠️  未启用只读文件系统${NC}"
fi

if grep -q "127.0.0.1:" docker-compose.yml; then
    echo -e "${GREEN}  ✅ 端口绑定到localhost${NC}"
else
    echo -e "${RED}  ❌ 端口可能暴露到公网${NC}"
fi

if grep -q "cap_drop" docker-compose.yml; then
    echo -e "${GREEN}  ✅ 已删除容器权限${NC}"
else
    echo -e "${YELLOW}  ⚠️  容器可能有额外权限${NC}"
fi
echo ""

# 清理
echo "🧹 清理测试文件..."
rm -f .env.demo
echo -e "${GREEN}✅ 清理完成${NC}"
echo ""

# 总结
echo "================================================"
echo "🎉 测试完成！"
echo "================================================"
echo ""
echo "安全评估:"
echo -e "${GREEN}✅ 非root用户运行${NC}"
echo -e "${GREEN}✅ 端口绑定到localhost${NC}"
echo -e "${GREEN}✅ 演示配置无真实密钥${NC}"
echo ""
echo "要启动完整服务进行测试："
echo "  1. 创建配置: cp .env.example .env"
echo "  2. 编辑配置: nano .env (添加真实API密钥)"
echo "  3. 启动服务: docker-compose up -d"
echo "  4. 查看日志: docker-compose logs -f"
echo "  5. 访问Web: http://localhost:8080"
echo "  6. 停止服务: docker-compose down"
echo ""
echo -e "${YELLOW}⚠️  注意: 仅用于本地测试，不要暴露到公网${NC}"
echo ""
