# ClawdBot Examples

完整的使用示例，展示ClawdBot的各种功能。

---

## 📋 示例列表

### 1. 基础Agent使用 (`01_basic_agent.py`)

**学习内容**:
- 创建AgentRuntime
- 创建Session
- 发送消息并处理响应
- 上下文管理

**运行**:
```bash
# 设置API密钥
export ANTHROPIC_API_KEY='your-key'
# 或
export OPENAI_API_KEY='your-key'

python examples/01_basic_agent.py
```

---

### 2. 使用工具 (`02_with_tools.py`)

**学习内容**:
- 加载和配置工具
- 设置工具权限
- 处理工具调用
- 查看工具指标

**运行**:
```bash
python examples/02_with_tools.py
```

---

### 3. 监控和健康检查 (`03_monitoring.py`)

**学习内容**:
- 设置健康检查
- 收集指标
- 导出Prometheus格式
- 使用Timer

**运行**:
```bash
python examples/03_monitoring.py
```

**输出示例**:
```
📊 Metrics:

Counters:
  agent_requests: 3.0

Histograms:
  agent_request_time:
    Count: 3
    Avg: 1.234s
    P95: 1.456s
```

---

### 4. REST API服务器 (`04_api_server.py`)

**学习内容**:
- 启动FastAPI服务器
- 使用健康检查端点
- 使用Agent Chat API
- 查看指标

**运行**:
```bash
python examples/04_api_server.py
```

**API测试**:
```bash
# 健康检查
curl http://localhost:8000/health

# 查看文档
open http://localhost:8000/docs

# Chat
curl -X POST http://localhost:8000/agent/chat \
  -H "X-API-Key: test" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo",
    "message": "Hello!",
    "model": "anthropic/claude-opus-4"
  }'

# 获取指标
curl http://localhost:8000/metrics
```

---

### 5. Telegram机器人 (`05_telegram_bot.py`)

**学习内容**:
- 设置Telegram channel
- 连接Agent到Telegram
- 处理消息
- 自动重连

**准备工作**:
1. 在Telegram搜索 @BotFather
2. 发送 `/newbot` 创建机器人
3. 获取bot token
4. 设置环境变量

**运行**:
```bash
export TELEGRAM_BOT_TOKEN='your-bot-token'
export ANTHROPIC_API_KEY='your-key'

python examples/05_telegram_bot.py
```

然后在Telegram给你的机器人发消息！

---

## 🚀 快速开始

### 安装依赖

```bash
# 基础依赖
poetry install

# 开发依赖（用于测试）
poetry install --with dev
```

### 设置API密钥

```bash
# Anthropic (推荐)
export ANTHROPIC_API_KEY='sk-ant-...'

# 或 OpenAI
export OPENAI_API_KEY='sk-...'
```

### 运行第一个示例

```bash
python examples/01_basic_agent.py
```

---

## 📖 更多资源

### 文档
- [CURRENT_STATUS.md](../CURRENT_STATUS.md) - 项目当前状态
- [AGENT_IMPLEMENTATION.md](../AGENT_IMPLEMENTATION.md) - Agent架构说明
- [API文档](http://localhost:8000/docs) - 运行示例4后访问

### 测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_runtime.py -v

# 查看覆盖率
pytest --cov=clawdbot --cov-report=html
open htmlcov/index.html
```

---

## 💡 常见问题

### Q: 示例运行失败，显示API密钥错误？

**A**: 确保设置了正确的环境变量：
```bash
# 检查是否设置
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# 如果为空，设置一个
export ANTHROPIC_API_KEY='your-key'
```

### Q: Telegram bot示例无法连接？

**A**: 
1. 确认bot token正确
2. 检查网络连接
3. 查看日志输出
4. 确保没有防火墙阻止

### Q: 如何切换模型？

**A**: 在创建AgentRuntime时指定：
```python
# 使用Claude
runtime = AgentRuntime(model="anthropic/claude-opus-4")

# 使用GPT-4
runtime = AgentRuntime(model="openai/gpt-4o")
```

### Q: 如何调整超时时间？

**A**: 配置工具或runtime：
```python
from clawdbot.agents.tools.base import ToolConfig

tool.configure(ToolConfig(
    timeout_seconds=60.0,  # 60秒超时
    max_output_size=200000
))
```

---

## 🎯 下一步

学完这些示例后，你可以：

1. **创建自己的工具** - 继承 `AgentTool` 类
2. **添加新的channel** - 继承 `ChannelPlugin` 类
3. **集成到你的应用** - 使用REST API
4. **部署到生产** - 使用Docker (见 `DOCKER_QUICKSTART.md`)

---

**Happy Coding!** 🚀
