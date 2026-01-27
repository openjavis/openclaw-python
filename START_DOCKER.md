# 🐳 Docker快速开始（安全版）

ClawdBot Python Docker安全测试指南

---

## 🎯 一键测试

```bash
# 下载并运行安全测试
chmod +x test-docker-safe.sh
./test-docker-safe.sh
```

---

## 📋 前置要求

- Docker Desktop 或 Docker Engine
- docker-compose
- 至少2GB可用内存

---

## 🚀 快速开始（3步骤）

### 步骤1: 创建配置

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置（可选：添加真实API密钥进行完整测试）
nano .env
```

**安全提示**: `.env`文件已在`.gitignore`中，不会被提交

### 步骤2: 构建并启动

```bash
# 构建镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d
```

### 步骤3: 访问服务

```bash
# Web UI（仅本地访问）
open http://localhost:8080

# 查看日志
docker-compose logs -f

# 检查状态
docker-compose ps
```

---

## 🔒 安全特性

### 已实施的安全措施

✅ **非root用户** - 容器以`clawdbot`用户运行（UID 1000）  
✅ **只读文件系统** - 防止恶意文件修改  
✅ **Localhost绑定** - 端口仅绑定到127.0.0.1  
✅ **无特权运行** - 删除所有容器特殊权限  
✅ **资源限制** - CPU 2核，内存2GB限制  
✅ **密钥隔离** - API密钥通过环境变量传递

### 安全验证

```bash
# 检查运行用户（应该是clawdbot，不是root）
docker-compose exec clawdbot whoami

# 检查端口绑定（应该是127.0.0.1）
netstat -tlnp | grep 18789

# 查看资源使用
docker stats clawdbot-test
```

---

## 🧪 测试模式（无需真实API密钥）

```bash
# 1. 创建测试配置
cat > .env << 'EOF'
ANTHROPIC_API_KEY=demo-test-key
OPENAI_API_KEY=demo-test-key
CLAWDBOT_ENV=demo
EOF

# 2. 启动测试
docker-compose up -d

# 3. 检查状态
docker-compose logs

# 4. 停止并清理
docker-compose down
rm .env
```

---

## 📊 常用命令

### 容器管理

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看日志
docker-compose logs -f

# 进入容器
docker-compose exec clawdbot bash

# 查看状态
docker-compose ps
```

### 清理

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi clawdbot-python-clawdbot

# 清理所有
docker-compose down --rmi all --volumes
```

---

## ⚠️ 重要安全提示

### ✅ 安全做法

- 仅在本地测试使用
- 不要暴露端口到公网（0.0.0.0）
- 使用`.env`文件管理密钥
- 定期更新Docker镜像
- 检查安全日志

### ❌ 不要做

- 不要在Dockerfile中硬编码密钥
- 不要将.env文件提交到git
- 不要绑定端口到0.0.0.0
- 不要在生产环境直接使用此配置
- 不要以root用户运行

---

## 🔍 故障排除

### 问题: 构建失败

```bash
# 清理Docker缓存并重建
docker-compose build --no-cache
```

### 问题: 端口已被占用

```bash
# 检查端口占用
lsof -i :18789
lsof -i :8080

# 修改端口（编辑docker-compose.yml）
ports:
  - "127.0.0.1:18790:18789"  # 改为18790
```

### 问题: 内存不足

```bash
# 减少资源限制（编辑docker-compose.yml）
limits:
  memory: 1G  # 从2G降到1G
```

---

## 📈 性能优化

### 资源调整

编辑`docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # 增加CPU
      memory: 4G       # 增加内存
    reservations:
      cpus: '1.0'
      memory: 1G
```

---

## 🎓 学习资源

- [DOCKER_SECURITY.md](DOCKER_SECURITY.md) - 详细安全指南
- [DOCKER_TEST_REPORT.md](DOCKER_TEST_REPORT.md) - 安全测试报告
- [README.md](README.md) - 项目文档
- [QUICKSTART.md](QUICKSTART.md) - 快速开始

---

## 💡 使用场景

### ✅ 适合用于

- **本地开发**: 隔离的开发环境
- **功能测试**: 验证新功能
- **学习研究**: 了解ClawdBot
- **Demo演示**: 展示功能

### ❌ 不适合

- **生产部署**: 需要额外安全配置
- **公网服务**: 需要防火墙和认证
- **多租户**: 需要更强的隔离
- **敏感数据**: 需要加密和审计

---

## 🆘 获取帮助

如果遇到问题:

1. 查看日志: `docker-compose logs`
2. 检查状态: `docker-compose ps`
3. 阅读文档: [DOCKER_SECURITY.md](DOCKER_SECURITY.md)
4. 运行测试: `./test-docker-safe.sh`

---

**版本**: 0.3.0  
**更新**: 2026-01-28  
**状态**: ✅ 已测试，本地使用安全

🎉 **享受安全的Docker体验！**
