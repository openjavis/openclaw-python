# 🚀 Docker 部署快速入门

## ⚡ 三步启动

### 第一步：安装 Docker Desktop

```bash
# 运行安装脚本
./install-docker.sh
```

**或手动安装：**

1. 下载 Docker Desktop for Mac (Intel):
   ```
   https://desktop.docker.com/mac/main/amd64/Docker.dmg
   ```

2. 安装步骤：
   - 双击 `Docker.dmg`
   - 拖动 Docker 到 Applications
   - 打开 Docker，等待启动（菜单栏会显示小鲸鱼图标）

3. 验证安装：
   ```bash
   docker --version
   docker compose version
   ```

---

### 第二步：配置环境变量

创建 `.env` 文件：

```bash
# 创建 .env 文件
cat > .env << 'EOF'
# Google Gemini API Key (必需)
GOOGLE_API_KEY=你的-API-Key

# Telegram Bot Token (必需)
TELEGRAM_BOT_TOKEN=你的-Bot-Token

# 可选配置
OPENCLAW_ENV=production
OPENCLAW_LOG_LEVEL=INFO
EOF
```

**或者编辑：**

```bash
nano .env
# 或
code .env
```

---

### 第三步：启动服务

```bash
# 使用快速启动脚本（推荐）
./docker-start.sh
# 选择 "1" (首次启动)

# 或手动启动
docker compose build
docker compose up -d
```

---

## 📊 管理命令

### 使用脚本（推荐）

```bash
./docker-start.sh
```

交互式菜单：
1. 首次启动（构建 + 运行）
2. 启动服务
3. 停止服务
4. 重启服务
5. 查看日志
6. 查看状态
7. 完全重建

### 手动命令

```bash
# 启动
docker compose up -d

# 停止
docker compose down

# 查看日志
docker compose logs -f

# 查看状态
docker compose ps

# 重启
docker compose restart

# 进入容器
docker compose exec openclaw bash
```

---

## ✅ 验证部署

### 1. 检查容器状态

```bash
docker compose ps
```

应该看到：
```
NAME                STATUS          PORTS
openclaw-python     Up (healthy)    127.0.0.1:8765->8765/tcp
```

### 2. 查看日志

```bash
docker compose logs --tail=50
```

应该看到类似输出：
```
✅ Loaded 33 tools
✅ Loaded 50 skills
✅ Skills prompt loaded (1556 chars)
✅ Agent Runtime 初始化完成
✅ Gateway Server started on ws://0.0.0.0:8765
```

### 3. 测试 WebSocket API

```bash
# 使用 curl (如果支持 WebSocket)
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8765
```

### 4. 测试 Telegram Bot

在 Telegram 中发送消息给你的 Bot：
```
你好！
帮我查询一下天气
分析这张照片 [发送图片]
```

---

## 🐛 常见问题

### 问题1: Docker 未运行

**错误信息:**
```
Cannot connect to the Docker daemon
```

**解决方法:**
```bash
# 1. 打开 Docker Desktop 应用
open -a Docker

# 2. 等待启动完成（菜单栏会显示小鲸鱼图标）

# 3. 验证
docker info
```

---

### 问题2: 端口被占用

**错误信息:**
```
Bind for 0.0.0.0:8765 failed: port is already allocated
```

**解决方法:**

**方案1: 停止占用端口的服务**
```bash
# 查找占用端口的进程
lsof -i :8765

# 杀死进程
kill -9 [PID]
```

**方案2: 修改端口**

编辑 `docker-compose.yml`：
```yaml
ports:
  - "127.0.0.1:8766:8765"  # 改用 8766 端口
```

---

### 问题3: 构建失败

**错误信息:**
```
failed to solve: failed to fetch
```

**解决方法:**
```bash
# 清理缓存
docker system prune -a

# 重新构建
docker compose build --no-cache
```

---

### 问题4: 容器不健康

**查看健康状态:**
```bash
docker inspect openclaw-python | grep -A 10 "Health"
```

**查看详细日志:**
```bash
docker compose logs openclaw
```

**重启容器:**
```bash
docker compose restart
```

---

### 问题5: API Key 错误

**错误信息:**
```
❌ 错误: 未找到 LLM API key
```

**解决方法:**
```bash
# 1. 检查 .env 文件
cat .env | grep API_KEY

# 2. 编辑 .env 文件
nano .env

# 3. 重启服务
docker compose down
docker compose up -d

# 4. 验证环境变量
docker compose exec openclaw env | grep API_KEY
```

---

### 问题6: Telegram Bot 无响应

**检查步骤:**

1. **检查 Token 是否正确:**
   ```bash
   grep TELEGRAM_BOT_TOKEN .env
   ```

2. **查看日志:**
   ```bash
   docker compose logs | grep -i telegram
   ```

3. **测试 Bot Token:**
   ```bash
   curl "https://api.telegram.org/bot你的TOKEN/getMe"
   ```

4. **重启服务:**
   ```bash
   docker compose restart
   ```

---

## 📈 性能优化

### 调整资源限制

编辑 `docker-compose.yml`：

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # 根据你的 CPU 调整
      memory: 8G       # 根据你的内存调整
```

### 查看资源使用

```bash
# 实时监控
docker stats openclaw-python

# 查看详细信息
docker compose exec openclaw top
```

---

## 🔒 安全提醒

### ✅ 已配置的安全措施

- ✅ 端口仅绑定到 localhost (127.0.0.1)
- ✅ 使用非 root 用户运行
- ✅ .env 文件不提交到 Git

### 📝 额外建议

1. **保护 .env 文件:**
   ```bash
   chmod 600 .env
   echo ".env" >> .gitignore
   ```

2. **定期更新:**
   ```bash
   git pull
   docker compose build
   docker compose up -d
   ```

3. **备份数据:**
   ```bash
   docker run --rm \
     -v openclaw-workspace:/data \
     -v $(pwd):/backup \
     alpine tar czf /backup/backup.tar.gz /data
   ```

---

## 📚 完整文档

详细的部署指南请参考：
- [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) - 完整部署文档
- [README.md](./README.md) - 项目说明

---

## 🎉 部署成功！

如果一切正常，你应该看到：

```bash
$ docker compose ps

NAME                STATUS          PORTS
openclaw-python     Up (healthy)    127.0.0.1:8765->8765/tcp
```

现在可以：
- ✅ 在 Telegram 中使用 AI 助手
- ✅ 通过 WebSocket API 连接
- ✅ 查看实时日志：`docker compose logs -f`

享受你的 AI 助手！🚀
