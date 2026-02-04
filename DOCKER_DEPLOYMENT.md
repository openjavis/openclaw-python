# 🐳 Docker 部署指南

## 📋 系统要求

### ✅ 你的系统（已检测）
- **操作系统**: macOS 12.7.6 (Monterey)
- **芯片架构**: Intel x86_64
- **Docker 兼容性**: ✅ 完全支持

### 最低要求
- macOS 12.0 或更高
- 4GB RAM（推荐 8GB+）
- 10GB 可用磁盘空间
- Intel 或 Apple Silicon 芯片

---

## 📥 第一步：安装 Docker Desktop

### 对于 macOS 12.7.6 (Monterey) + Intel

#### 推荐版本：Docker Desktop 4.25.x

**下载链接：**
```
https://desktop.docker.com/mac/main/amd64/Docker.dmg
```

或访问官网选择适合的版本：
```
https://docs.docker.com/desktop/install/mac-install/
```

#### 安装步骤：

1. **下载 Docker Desktop**
   ```bash
   # 方式1：直接下载
   open "https://desktop.docker.com/mac/main/amd64/Docker.dmg"
   
   # 方式2：使用 brew (如果已安装 Homebrew)
   brew install --cask docker
   ```

2. **安装应用**
   - 双击下载的 `Docker.dmg`
   - 将 Docker 图标拖到 Applications 文件夹
   - 打开 Applications，双击 Docker

3. **初次启动**
   - Docker 会要求授权（输入密码）
   - 等待 Docker 引擎启动（状态栏会显示小鲸鱼图标）
   - 看到 "Docker Desktop is running" 即可

4. **验证安装**
   ```bash
   # 检查 Docker 版本
   docker --version
   # 应该显示：Docker version 4.x.x
   
   # 检查 Docker Compose
   docker compose version
   # 应该显示：Docker Compose version v2.x.x
   
   # 测试运行
   docker run hello-world
   ```

#### 可能的问题：

**问题1：无法打开 Docker（提示已损坏）**
```bash
# 解决方法：移除隔离属性
sudo xattr -rd com.apple.quarantine /Applications/Docker.app
```

**问题2：Docker 启动失败**
```bash
# 解决方法：重置 Docker
# 1. 完全退出 Docker
# 2. 删除配置文件
rm -rf ~/Library/Group\ Containers/group.com.docker
rm -rf ~/Library/Containers/com.docker.docker
# 3. 重新启动 Docker
```

---

## 🚀 第二步：配置项目

### 1. 复制环境变量模板

```bash
cd /Users/openbot/Desktop/openclaw-python

# 复制环境变量模板
cp .env.docker .env

# 编辑 .env 文件，填入你的 API 密钥
nano .env
# 或使用其他编辑器：code .env 或 open -a TextEdit .env
```

### 2. 必需配置

在 `.env` 文件中至少配置以下内容：

```bash
# 必需：至少一个 LLM API Key
GOOGLE_API_KEY=你的-Google-API-Key

# 必需（如果使用 Telegram）
TELEGRAM_BOT_TOKEN=你的-Telegram-Bot-Token
```

---

## 🏗️ 第三步：构建和运行

### 方式 1：使用 Docker Compose（推荐）

```bash
# 1. 构建镜像
docker compose build

# 2. 启动服务
docker compose up -d

# 3. 查看日志
docker compose logs -f

# 4. 查看状态
docker compose ps

# 5. 停止服务
docker compose down
```

### 方式 2：使用 Docker 命令

```bash
# 1. 构建镜像
docker build -t openclaw-python:latest .

# 2. 运行容器
docker run -d \
  --name openclaw \
  -p 127.0.0.1:8765:8765 \
  --env-file .env \
  -v openclaw-workspace:/app/workspace \
  openclaw-python:latest

# 3. 查看日志
docker logs -f openclaw

# 4. 停止容器
docker stop openclaw

# 5. 删除容器
docker rm openclaw
```

---

## 📊 管理和监控

### 查看运行状态

```bash
# 查看所有容器
docker ps -a

# 查看资源使用
docker stats openclaw-python

# 进入容器
docker exec -it openclaw-python bash

# 查看实时日志
docker compose logs -f openclaw
```

### 重启服务

```bash
# 重启容器
docker compose restart

# 完全重建
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 数据备份

```bash
# 备份 workspace 数据
docker run --rm -v openclaw-workspace:/data -v $(pwd):/backup \
  alpine tar czf /backup/openclaw-workspace-backup.tar.gz /data

# 恢复 workspace 数据
docker run --rm -v openclaw-workspace:/data -v $(pwd):/backup \
  alpine tar xzf /backup/openclaw-workspace-backup.tar.gz -C /
```

---

## 🐛 故障排查

### 问题1：容器无法启动

```bash
# 查看详细错误
docker compose logs openclaw

# 检查配置
docker compose config

# 重建镜像
docker compose build --no-cache
```

### 问题2：API Key 错误

```bash
# 检查环境变量
docker compose exec openclaw env | grep API_KEY

# 重新加载环境变量
docker compose down
docker compose up -d
```

### 问题3：端口冲突

```bash
# 检查端口占用
lsof -i :8765

# 修改 docker-compose.yml 中的端口映射
# 例如：改为 "127.0.0.1:8766:8765"
```

### 问题4：内存不足

```bash
# 增加 Docker 内存限制（在 Docker Desktop 设置中）
# Settings -> Resources -> Memory -> 调整到 4GB+

# 或修改 docker-compose.yml 中的资源限制
```

---

## 🔒 安全建议

### 1. 保护 API Keys

```bash
# 确保 .env 文件不被提交
echo ".env" >> .gitignore

# 设置文件权限
chmod 600 .env
```

### 2. 仅本地访问

docker-compose.yml 已配置端口绑定到 localhost：
```yaml
ports:
  - "127.0.0.1:8765:8765"  # 仅本地访问
```

### 3. 定期更新

```bash
# 拉取最新代码
git pull

# 重建镜像
docker compose build --no-cache
docker compose up -d
```

---

## 📈 性能优化

### 1. 调整资源限制

编辑 `docker-compose.yml`：

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # 增加 CPU 限制
      memory: 8G       # 增加内存限制
    reservations:
      cpus: '1.0'
      memory: 2G
```

### 2. 使用 BuildKit

```bash
# 启用 BuildKit 加速构建
export DOCKER_BUILDKIT=1
docker compose build
```

### 3. 清理未使用资源

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的卷
docker volume prune

# 清理所有未使用资源
docker system prune -a --volumes
```

---

## 🧪 测试部署

### 1. 健康检查

```bash
# 检查容器健康状态
docker inspect openclaw-python | grep -A 5 "Health"

# 手动健康检查
docker compose exec openclaw python -c "import openclaw; print('OK')"
```

### 2. 测试 WebSocket API

```bash
# 使用 wscat (需要先安装: npm install -g wscat)
wscat -c ws://localhost:8765

# 或使用 Python
python3 << 'EOF'
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # 发送 ping
        await websocket.send(json.dumps({"type": "req", "id": "1", "method": "ping"}))
        response = await websocket.recv()
        print(f"收到响应: {response}")

asyncio.run(test())
EOF
```

### 3. 测试 Telegram Bot

在 Telegram 中发送消息给你的 Bot，应该能收到响应。

---

## 📚 快速命令参考

### 常用命令

```bash
# 启动
docker compose up -d

# 停止
docker compose down

# 重启
docker compose restart

# 查看日志
docker compose logs -f

# 查看状态
docker compose ps

# 进入容器
docker compose exec openclaw bash

# 更新并重启
git pull && docker compose build && docker compose up -d
```

### 维护命令

```bash
# 查看资源使用
docker stats

# 清理系统
docker system prune -a

# 备份数据
docker run --rm -v openclaw-workspace:/data -v $(pwd):/backup alpine tar czf /backup/backup.tar.gz /data

# 查看网络
docker network ls
docker network inspect openclaw-net
```

---

## ✅ 部署检查清单

- [ ] Docker Desktop 已安装并运行
- [ ] 已复制 `.env.docker` 到 `.env`
- [ ] 已配置至少一个 LLM API Key
- [ ] 已配置 Telegram Bot Token（如果使用）
- [ ] 运行 `docker compose build` 成功
- [ ] 运行 `docker compose up -d` 成功
- [ ] 容器状态为 "Up (healthy)"
- [ ] 可以访问 ws://localhost:8765
- [ ] Telegram Bot 响应正常
- [ ] 日志无错误

---

## 🆘 获取帮助

### 查看日志

```bash
# 实时日志
docker compose logs -f

# 最近100行
docker compose logs --tail=100

# 特定服务
docker compose logs openclaw
```

### 调试模式

```bash
# 启用调试日志
docker compose down
echo "OPENCLAW_LOG_LEVEL=DEBUG" >> .env
docker compose up -d
```

---

## 🎉 部署成功！

如果一切正常，你应该看到：

```
✅ Container: openclaw-python (Up, healthy)
✅ WebSocket API: ws://localhost:8765
✅ Telegram Bot: 运行中
✅ 日志: 无错误
```

现在可以在 Telegram 中使用你的 AI 助手了！🚀
