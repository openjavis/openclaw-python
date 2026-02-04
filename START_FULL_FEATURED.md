# 🦞 OpenClaw Python - 功能最全启动指南

## 📊 启动方式对比

OpenClaw 提供 3 种启动方式，功能从简单到完整：

### 方式 1️⃣：直接 Telegram Bot（简单快速）

**命令：**
```bash
uv run python examples/05_telegram_bot.py
```

**功能：**
- ✅ Telegram Bot
- ✅ Agent Runtime
- ✅ Session 管理
- ❌ 无 WebSocket API
- ❌ 无多频道管理
- ❌ 无事件广播

**适用场景：**
- 快速测试
- 单一 Telegram Bot
- 简单对话应用

---

### 方式 2️⃣：HTTP API 服务器（API 集成）

**命令：**
```bash
uv run openclaw api start
```

**功能：**
- ✅ RESTful API
- ✅ OpenAI 兼容接口
- ✅ Agent Runtime
- ✅ Swagger 文档
- ❌ 无频道集成
- ❌ 无 WebSocket

**适用场景：**
- API 集成
- 自定义客户端
- HTTP 调用

---

### 方式 3️⃣：Gateway + Channel（功能最全）⭐

**命令：**
```bash
uv run python examples/10_gateway_telegram_bridge.py
```

**功能：**
- ✅ Gateway Server（核心）
- ✅ Channel Manager（频道管理）
- ✅ WebSocket API（实时通信）
- ✅ Event Broadcasting（事件广播）
- ✅ 多频道支持（Telegram、Discord、Slack）
- ✅ 外部客户端支持（Web UI、CLI、Mobile）
- ✅ Observer 模式（事件监听）
- ✅ 完整架构（匹配 TypeScript 官方版本）

**适用场景：**
- ✅ **生产环境（推荐）**
- ✅ 多频道接入
- ✅ 需要 WebSocket API
- ✅ 需要实时事件
- ✅ 企业级应用

---

## 🏗️ 方式 3 完整架构

```
┌────────────────────────────────────────────────────────────┐
│              OpenClaw Server (单进程)                       │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │            Gateway Server                        │    │
│  │                                                  │    │
│  │  【1. Channel Manager】                          │    │
│  │  ├─ Telegram Channel (Plugin)                   │    │
│  │  ├─ Discord Channel (Plugin)                    │    │
│  │  ├─ Slack Channel (Plugin)                      │    │
│  │  └─ ...更多频道                                  │    │
│  │                                                  │    │
│  │  【2. WebSocket Server】                         │    │
│  │  └─ ws://localhost:8765                         │    │
│  │     (供外部客户端连接)                            │    │
│  │                                                  │    │
│  │  【3. Event Broadcasting】                       │    │
│  │  └─ 实时广播 Agent 事件到所有客户端              │    │
│  └──────────────────────────────────────────────────┘    │
│                        ↑                                   │
│                    观察/监听                                │
│  ┌──────────────────┴─────────────────────────────┐      │
│  │         Agent Runtime（AI 核心）                │      │
│  │  • 处理消息                                    │      │
│  │  • 调用 LLM API (Gemini/GPT/Claude)           │      │
│  │  • 工具调用 (Browser/Bash/File...)            │      │
│  │  • 发出事件                                    │      │
│  └────────────────────────────────────────────────┘      │
└────────────────────────────────────────────────────────────┘
         ↓                                    ↕
    平台 API                              WebSocket
  (Telegram/Discord...)              (UI/CLI/Mobile)
```

---

## 🚀 功能最全启动（推荐）

### 前提条件

1. ✅ 已安装依赖
2. ✅ 已配置 `.env`
3. ✅ 至少一个 LLM API Key
4. ✅ （可选）Telegram/Discord Bot Token

### 启动步骤

#### 快速启动

```bash
cd /Users/openbot/Desktop/openclaw-python
export PATH="$HOME/.local/bin:$PATH"
uv run python examples/10_gateway_telegram_bridge.py
```

#### 使用启动脚本（推荐）

```bash
cd /Users/openbot/Desktop/openclaw-python
./start_full_server.sh
```

---

## 🎯 Gateway 提供的功能

### 1. Channel Manager（频道管理器）

**作用：** 统一管理所有频道（Telegram、Discord、Slack 等）

**功能：**
- 动态注册/注销频道
- 频道生命周期管理（start/stop/restart）
- 独立配置每个频道
- 频道状态监控
- 频道事件通知

**示例：**
```python
# 注册 Telegram 频道
channel_manager.register(
    channel_id="telegram",
    channel_class=EnhancedTelegramChannel,
    config={"bot_token": "..."}
)

# 注册 Discord 频道
channel_manager.register(
    channel_id="discord",
    channel_class=EnhancedDiscordChannel,
    config={"bot_token": "..."}
)

# 启动所有频道
await gateway.start(start_channels=True)
```

### 2. WebSocket API（实时通信）

**端点：** `ws://localhost:8765`

**作用：** 为外部客户端提供实时 API

**支持的方法：**
- `connect` - 建立连接
- `agent` - 发送消息给 AI
- `send` - 发送消息到频道
- `channels.list` - 列出所有频道
- `channels.start` - 启动频道
- `channels.stop` - 停止频道
- `sessions.list` - 列出会话
- `sessions.get` - 获取会话详情

**客户端类型：**
- 🌐 Web UI（浏览器）
- 📱 移动应用（iOS/Android）
- 💻 CLI 工具
- 🔧 自定义集成

### 3. Event Broadcasting（事件广播）

**作用：** 实时广播 Agent 事件到所有连接的客户端

**事件类型：**
- `agent` - Agent 运行时事件
  - `text` - 文本输出
  - `tool_call` - 工具调用
  - `thinking` - 思考过程
  - `error` - 错误信息
- `channel` - 频道事件
  - `started` - 频道启动
  - `stopped` - 频道停止
  - `message` - 新消息
  - `error` - 频道错误

**使用场景：**
- 实时监控 AI 对话
- 多客户端同步
- 调试和日志
- 性能监控

---

## 📋 配置说明

### 环境变量（.env）

```bash
# LLM API Keys（至少配置一个）
GOOGLE_API_KEY=your-google-api-key      # ✅ 当前使用
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...

# 频道配置
TELEGRAM_BOT_TOKEN=your-telegram-token   # ✅ 已配置
# DISCORD_BOT_TOKEN=your-discord-token
# SLACK_BOT_TOKEN=your-slack-token

# Gateway 配置
GATEWAY_PORT=8765                         # WebSocket 端口
GATEWAY_BIND=loopback                     # 绑定地址

# Agent 配置
AGENT_MODEL=gemini/gemini-3-flash-preview # ✅ 当前模型
AGENT_MAX_TOKENS=4000
```

### 代码配置（可选）

编辑 `examples/10_gateway_telegram_bridge.py`:

```python
# 修改配置
config = ClawdbotConfig(
    gateway={
        "port": 8765,              # WebSocket 端口
        "bind": "loopback",        # 只允许本地连接
    },
    agent={
        "model": "gemini/gemini-3-flash-preview",
        "max_tokens": 4000,
    },
)
```

---

## 🔌 连接外部客户端

### 使用 JavaScript/TypeScript

```javascript
const ws = new WebSocket('ws://localhost:8765');

// 1. 握手连接
ws.send(JSON.stringify({
  type: 'req',
  id: '1',
  method: 'connect',
  params: {
    maxProtocol: 1,
    client: {
      name: 'my-app',
      version: '1.0.0',
      platform: 'web'
    }
  }
}));

// 2. 发送消息给 AI
ws.send(JSON.stringify({
  type: 'req',
  id: '2',
  method: 'agent',
  params: {
    message: 'Hello AI!',
    sessionId: 'my-session'
  }
}));

// 3. 接收事件
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data);
  
  if (data.type === 'event' && data.event === 'agent') {
    // Agent 事件
    console.log('Agent:', data.payload);
  }
};
```

### 使用 Python

```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        # 1. 连接
        await ws.send(json.dumps({
            "type": "req",
            "id": "1",
            "method": "connect",
            "params": {
                "maxProtocol": 1,
                "client": {
                    "name": "python-client",
                    "version": "1.0.0"
                }
            }
        }))
        
        # 2. 发送消息
        await ws.send(json.dumps({
            "type": "req",
            "id": "2",
            "method": "agent",
            "params": {
                "message": "你好!",
                "sessionId": "test-session"
            }
        }))
        
        # 3. 接收消息
        async for message in ws:
            data = json.loads(message)
            print(f"Received: {data}")

asyncio.run(connect())
```

### 使用 wscat（测试工具）

```bash
# 安装 wscat
npm install -g wscat

# 连接
wscat -c ws://localhost:8765

# 发送连接请求
> {"type":"req","id":"1","method":"connect","params":{"maxProtocol":1,"client":{"name":"wscat"}}}

# 发送消息
> {"type":"req","id":"2","method":"agent","params":{"message":"Hello!","sessionId":"test"}}
```

---

## 📊 功能对比总结

| 功能 | 直接 Bot | API 服务器 | Gateway（完整）|
|-----|---------|-----------|---------------|
| Telegram Bot | ✅ | ❌ | ✅ |
| Discord Bot | ❌ | ❌ | ✅ |
| 多频道支持 | ❌ | ❌ | ✅ |
| HTTP API | ❌ | ✅ | ❌ |
| WebSocket API | ❌ | ❌ | ✅ |
| 实时事件 | ❌ | ❌ | ✅ |
| 频道管理 | ❌ | ❌ | ✅ |
| 外部客户端 | ❌ | ✅ | ✅ |
| 事件广播 | ❌ | ❌ | ✅ |
| 生产就绪 | ⚠️ | ✅ | ✅ |

---

## 🎯 推荐使用场景

### 使用直接 Bot（方式 1）
- ✅ 快速测试
- ✅ 学习和开发
- ✅ 单一 Telegram Bot
- ❌ 不适合生产

### 使用 API 服务器（方式 2）
- ✅ API 集成
- ✅ 自定义客户端
- ✅ HTTP 调用
- ❌ 不需要频道

### 使用 Gateway（方式 3）⭐ **推荐**
- ✅ **生产环境**
- ✅ 多频道接入
- ✅ 企业应用
- ✅ 需要实时性
- ✅ 完整功能

---

## 🔧 管理命令

### 启动完整服务器

```bash
cd /Users/openbot/Desktop/openclaw-python
./start_full_server.sh
```

### 查看服务状态

```bash
./check_server_status.sh
```

### 查看实时日志

```bash
tail -f /tmp/openclaw_server.log
```

### 停止服务

```bash
pkill -f "10_gateway_telegram_bridge"
```

---

## 📚 更多资源

- **完整文档**: `README.md`
- **架构说明**: `docs/PYTHON_VS_TYPESCRIPT_ARCHITECTURE.md`
- **示例代码**: `examples/`
- **API 文档**: WebSocket 连接后查看

---

## 💡 总结

**功能最全的启动方式：**

```bash
# 一键启动完整服务器
cd /Users/openbot/Desktop/openclaw-python
uv run python examples/10_gateway_telegram_bridge.py
```

**提供：**
- ✅ Gateway Server
- ✅ Channel Manager
- ✅ WebSocket API (ws://localhost:8765)
- ✅ Event Broadcasting
- ✅ 多频道支持
- ✅ 外部客户端支持
- ✅ 生产就绪

**适合：**
- 生产环境部署
- 多频道接入需求
- 需要 WebSocket API
- 企业级应用

🦞 **OpenClaw Python - 完整架构，生产就绪！**
