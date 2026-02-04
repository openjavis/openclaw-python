#!/bin/bash
# Docker Desktop 安装脚本 (macOS 12.7.6 Monterey)

echo "🐳 OpenClaw Python - Docker Desktop 安装向导"
echo "========================================"
echo ""

# 检查系统版本
echo "📋 检查系统信息..."
sw_vers
echo ""

# 检查 Docker 是否已安装
if command -v docker &> /dev/null; then
    echo "✅ Docker 已安装"
    docker --version
    docker compose version
    echo ""
    echo "如需重新安装，请先卸载现有版本："
    echo "  1. 退出 Docker Desktop"
    echo "  2. 删除 /Applications/Docker.app"
    echo "  3. 重新运行此脚本"
    exit 0
fi

echo "📥 Docker 未安装，准备安装..."
echo ""

# 检查是否有 Homebrew
if command -v brew &> /dev/null; then
    echo "✅ 检测到 Homebrew"
    echo ""
    echo "选项 1: 使用 Homebrew 安装 (推荐)"
    echo "选项 2: 手动下载安装"
    echo ""
    read -p "请选择安装方式 (1/2): " choice
    
    if [ "$choice" == "1" ]; then
        echo ""
        echo "🍺 使用 Homebrew 安装 Docker Desktop..."
        brew install --cask docker
        
        echo ""
        echo "✅ Docker Desktop 安装完成！"
        echo ""
        echo "📝 下一步："
        echo "  1. 打开 Applications 文件夹"
        echo "  2. 双击 Docker 应用"
        echo "  3. 授权并等待 Docker 启动"
        echo "  4. 看到菜单栏的小鲸鱼图标即可"
        echo ""
        exit 0
    fi
fi

echo "📥 准备手动下载 Docker Desktop..."
echo ""
echo "下载地址:"
echo "  https://desktop.docker.com/mac/main/amd64/Docker.dmg"
echo ""
echo "或访问官网选择版本:"
echo "  https://docs.docker.com/desktop/install/mac-install/"
echo ""
read -p "是否自动打开下载页面? (y/n): " open_browser

if [ "$open_browser" == "y" ]; then
    open "https://desktop.docker.com/mac/main/amd64/Docker.dmg"
    echo ""
    echo "✅ 已打开下载页面"
fi

echo ""
echo "📝 手动安装步骤:"
echo "  1. 下载 Docker.dmg"
echo "  2. 双击打开 DMG 文件"
echo "  3. 将 Docker 拖到 Applications 文件夹"
echo "  4. 打开 Applications，双击 Docker"
echo "  5. 授权并等待启动完成"
echo ""
echo "❓ 遇到问题？"
echo "  问题1: 提示已损坏"
echo "    解决: sudo xattr -rd com.apple.quarantine /Applications/Docker.app"
echo ""
echo "  问题2: 无法启动"
echo "    解决: 删除配置文件后重试"
echo "    rm -rf ~/Library/Group\\ Containers/group.com.docker"
echo "    rm -rf ~/Library/Containers/com.docker.docker"
echo ""
