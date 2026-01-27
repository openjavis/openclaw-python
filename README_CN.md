# ClawdBot Python 中文说明

**个人AI助手平台 - Python实现**

---

## 📢 项目状态

**版本**: 0.3.0  
**状态**: 🚧 **核心功能完成，正在积极追赶TypeScript版本（约80-90%）**

**重要**: 
- ❌ 不是"100%完成"
- ✅ 核心功能可用
- 🚧 持续改进中

**详细说明**: [CURRENT_STATUS.md](CURRENT_STATUS.md)

---

## 🤖 Agent实现

**本项目不使用Pi Agent**，而是**自研的AgentRuntime**。

```python
自研实现:
├── AgentRuntime (核心)
├── Session管理
├── 24个工具
├── 支持Claude + OpenAI
└── 完全自主可控
```

**详细说明**: [AGENT_IMPLEMENTATION.md](AGENT_IMPLEMENTATION.md)

---

## ✅ 核心功能

### 1. Agent Runtime ✅
- 自研实现（不用Pi Agent）
- 支持Claude和OpenAI
- 流式响应
- 工具调用

### 2. 工具系统 ✅ 24个工具
- 文件操作: read_file, write_file, edit_file
- Shell: bash
- Web: web_fetch, web_search
- 浏览器: browser (Playwright)
- 消息: message, *_actions
- 高级: image, cron, tts, etc.

### 3. Channel系统 🚧 17个频道
- **框架完整**: ✅ 
- **需要测试**: 🚧
  - Telegram, Discord, Slack
  - WhatsApp, Signal, Google Chat
  - iMessage, Teams, LINE
  - 等等...

### 4. Skills ✅ 52个技能
- Notion, Obsidian, Apple Notes
- Git, Docker, GitHub
- 1Password, Spotify, Trello
- macOS, Linux, Network
- 等等...

### 5. Gateway/API ✅
- WebSocket Gateway
- HTTP API
- OpenAI兼容API

---

## 🚀 快速开始

### 安装

```bash
# Poetry（推荐）
poetry install

# Pip
pip install -e .
```

### 配置

```bash
# 配置向导
clawdbot onboard

# 或手动设置
export ANTHROPIC_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

### 使用

```bash
# 启动Gateway
clawdbot gateway start

# 运行Agent
clawdbot agent --message "你好！"

# 管理频道
clawdbot channels list
clawdbot channels login telegram

# 检查状态
clawdbot status
```

**详细步骤**: [QUICKSTART.md](QUICKSTART.md)

---

## 🐳 Docker测试

安全的Docker环境配置：

```bash
# 运行安全测试
chmod +x test-docker-safe.sh
./test-docker-safe.sh

# 或手动启动
docker-compose build
docker-compose up -d
```

**安全评估**: 8.5/10 - 本地测试安全

**详细说明**:
- [DOCKER_完成总结.md](DOCKER_完成总结.md) - 总结
- [SECURITY_SUMMARY_CN.md](SECURITY_SUMMARY_CN.md) - 安全评估
- [DOCKER_SECURITY.md](DOCKER_SECURITY.md) - Security guide

---

## 📚 文档导览

### 必读

1. **[CURRENT_STATUS.md](CURRENT_STATUS.md)** ⭐ - 项目真实状态
2. **[AGENT_IMPLEMENTATION.md](AGENT_IMPLEMENTATION.md)** ⭐ - Agent实现
3. **[00_从这里开始_START_HERE.md](00_从这里开始_START_HERE.md)** - 开始指南
4. **[QUICKSTART.md](QUICKSTART.md)** - 快速开始

### Agent相关

- [AGENT_IMPLEMENTATION.md](AGENT_IMPLEMENTATION.md) - 详细架构
- `clawdbot/agents/runtime.py` - Runtime代码
- `clawdbot/agents/session.py` - Session管理
- `clawdbot/agents/tools/` - 24个工具

### Docker相关

- [DOCKER_完成总结.md](DOCKER_完成总结.md) - Docker总结
- [SECURITY_SUMMARY_CN.md](SECURITY_SUMMARY_CN.md) - 安全评估
- [START_DOCKER.md](START_DOCKER.md) - 使用指南

### 其他

- [ALL_FEATURES.md](ALL_FEATURES.md) - 功能列表
- [COMPARISON_REPORT.md](COMPARISON_REPORT.md) - 与TS对比
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南

---

## ❓ 常见问题

### Q: 项目完成度？

**A**: 约80-90%
- 代码: 90-95%
- 测试: 60-70%
- 可用性: 80-90%

### Q: 使用Pi Agent吗？

**A**: **不使用**。自研AgentRuntime。

详见: [AGENT_IMPLEMENTATION.md](AGENT_IMPLEMENTATION.md)

### Q: 哪些可以直接用？

**A**: 
- ✅ Agent基础功能
- ✅ WebChat
- 🚧 Telegram/Discord/Slack（需配置）

### Q: 生产环境可用吗？

**A**: 
- ✅ 本地测试 - 可以
- 🚧 生产环境 - 需更多测试
- ❌ 关键业务 - 暂不建议

### Q: Docker安全吗？

**A**: 本地测试安全（8.5/10）

详见: [SECURITY_SUMMARY_CN.md](SECURITY_SUMMARY_CN.md)

---

## 🛠️ 技术栈

- **Python**: 3.11+
- **异步**: asyncio, aiofiles
- **Web**: FastAPI, uvicorn, WebSocket
- **LLM**: Anthropic Claude, OpenAI
- **数据**: Pydantic, SQLite, LanceDB
- **工具**: Playwright, DuckDuckGo, etc.

---

## 🎯 实际情况

### 已完成 ✅

- Agent Runtime（自研）
- 24个工具
- 17个channel框架
- 52个skills
- Gateway和API
- 完整文档

### 还需要 🚧

- 真实API测试
- 生产环境验证
- 更多错误处理
- 性能优化

---

## 📈 与TypeScript对比

| 组件 | TypeScript | Python | 说明 |
|------|-----------|--------|------|
| Agent | Pi Agent? | 自研Runtime | ✅ 功能相似 |
| Tools | 24+ | 24 | ✅ 基本一致 |
| Channels | 17+ | 17 | 🚧 需测试 |
| Skills | 52 | 52 | ✅ 已移植 |
| Gateway | ✅ | ✅ | ✅ 一致 |

**总体**: 80-90%功能对等

---

## 🚀 未来计划

### 短期（1-2月）

- 🧪 真实API测试
- 🐛 Bug修复
- 📖 文档完善
- ⚡ 性能优化

### 中期（3-6月）

- ✨ 功能增强
- 🔒 安全加固
- 📊 监控日志
- 🧪 测试覆盖

---

## 🤝 贡献

欢迎贡献！

特别需要：
1. 🧪 真实API测试
2. 🐛 Bug报告
3. 📖 文档改进
4. ✨ 新功能

详见: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📜 许可证

MIT License

---

## 🙏 鸣谢

- 原始项目: [ClawdBot (TypeScript)](https://github.com/badlogic/clawdbot)
- LLM: Anthropic Claude, OpenAI

---

**版本**: 0.3.0  
**更新**: 2026-01-28  
**状态**: 🚧 核心完成，持续改进

**诚实、透明、持续进步** ✨
