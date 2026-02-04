#!/bin/bash
# OpenClaw Python - Docker 快速启动脚本

set -e  # 遇到错误立即退出

echo "🐳 OpenClaw Python - Docker 启动"
echo "=================================="
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行"
    echo ""
    echo "请先启动 Docker Desktop:"
    echo "  1. 打开 Applications 文件夹"
    echo "  2. 双击 Docker 应用"
    echo "  3. 等待菜单栏出现小鲸鱼图标"
    echo "  4. 重新运行此脚本"
    exit 1
fi

echo "✅ Docker 正在运行"
echo ""

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件"
    echo ""
    echo "创建 .env 文件..."
    
    cat > .env << 'EOF'
# OpenClaw Python - Environment Variables
# 请填入你的 API Keys

# Google Gemini API Key (必需)
GOOGLE_API_KEY=your-google-api-key-here

# Telegram Bot Token (必需，如果使用 Telegram)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# Optional
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=
# DISCORD_BOT_TOKEN=

# Application Settings
OPENCLAW_ENV=production
OPENCLAW_LOG_LEVEL=INFO
EOF
    
    echo "✅ 已创建 .env 文件"
    echo ""
    echo "📝 请编辑 .env 文件，填入你的 API Keys:"
    echo "   nano .env"
    echo ""
    echo "配置完成后，重新运行此脚本"
    exit 0
fi

echo "✅ 找到 .env 文件"
echo ""

# 检查 API Key
if grep -q "your-google-api-key-here" .env; then
    echo "⚠️  请先在 .env 文件中配置 API Keys"
    echo ""
    echo "编辑命令:"
    echo "  nano .env"
    echo ""
    exit 1
fi

echo "✅ API Keys 已配置"
echo ""

# 询问操作
echo "请选择操作:"
echo "  1. 首次启动（构建 + 运行）"
echo "  2. 启动服务"
echo "  3. 停止服务"
echo "  4. 重启服务"
echo "  5. 查看日志"
echo "  6. 查看状态"
echo "  7. 完全重建"
echo ""
read -p "请选择 (1-7): " choice

case $choice in
    1)
        echo ""
        echo "🏗️  构建 Docker 镜像..."
        docker compose build
        
        echo ""
        echo "🚀 启动服务..."
        docker compose up -d
        
        echo ""
        echo "⏳ 等待服务就绪..."
        sleep 10
        
        echo ""
        echo "📊 服务状态:"
        docker compose ps
        
        echo ""
        echo "✅ 部署完成！"
        echo ""
        echo "查看日志: docker compose logs -f"
        echo "WebSocket API: ws://localhost:8765"
        ;;
    
    2)
        echo ""
        echo "🚀 启动服务..."
        docker compose up -d
        
        echo ""
        docker compose ps
        echo ""
        echo "✅ 服务已启动"
        ;;
    
    3)
        echo ""
        echo "⏹️  停止服务..."
        docker compose down
        
        echo ""
        echo "✅ 服务已停止"
        ;;
    
    4)
        echo ""
        echo "🔄 重启服务..."
        docker compose restart
        
        echo ""
        docker compose ps
        echo ""
        echo "✅ 服务已重启"
        ;;
    
    5)
        echo ""
        echo "📋 查看日志 (Ctrl+C 退出)..."
        docker compose logs -f
        ;;
    
    6)
        echo ""
        echo "📊 服务状态:"
        docker compose ps
        
        echo ""
        echo "💻 资源使用:"
        docker stats --no-stream openclaw-python
        
        echo ""
        echo "🏥 健康检查:"
        docker inspect openclaw-python | grep -A 5 "Health" || echo "无健康检查信息"
        ;;
    
    7)
        echo ""
        echo "⚠️  这将删除所有容器和镜像，重新构建"
        read -p "确定继续? (y/n): " confirm
        
        if [ "$confirm" == "y" ]; then
            echo ""
            echo "🗑️  清理旧容器和镜像..."
            docker compose down
            docker rmi openclaw-python:latest 2>/dev/null || true
            
            echo ""
            echo "🏗️  重新构建..."
            docker compose build --no-cache
            
            echo ""
            echo "🚀 启动服务..."
            docker compose up -d
            
            echo ""
            echo "✅ 重建完成"
        fi
        ;;
    
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "📚 更多命令:"
echo "  docker compose logs -f      # 实时日志"
echo "  docker compose ps           # 查看状态"
echo "  docker compose exec openclaw bash  # 进入容器"
echo ""
