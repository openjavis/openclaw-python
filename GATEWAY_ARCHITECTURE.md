# Gateway 架构说明

> OpenClaw Python 的 Gateway 连接架构详解

---

## 📋 目录

1. [架构概览](#架构概览)
2. [TypeScript 官方实现](#typescript-官方实现)
3. [Python 实现](#python-实现)
4. [Telegram Bot 连接流程](#telegram-bot-连接流程)
5. [完整示例](#完整示例)

---

## 架构概览

### 三种连接模式

OpenClaw 支持三种不同的连接模式：

#### 模式 1: 直接 Bot（最简单）

```
Telegram 用户 → Telegram Bot API → Python Bot → Agent
```

- **优点**: 简单直接，快速上手
- **缺点**: 每个 channel 独立运行，难以统一管理
- **适用**: 单一 Telegram bot，快速测试

#### 模式 2: 集成服务器（推荐）⭐

```
┌─────────────────────────────────────────────┐
│         OpenClaw Server (单进程)             │
│                                             │
│  ┌────────────┐        ┌─────────────────┐ │
│  │  Gateway   │◄──────►│   Channel       │ │
│  │  Server    │        │   Plugins       │ │
│  │ (WebSocket)│        │  - Telegram Bot │ │
│  └──────▲─────┘        │  - Discord Bot  │ │
│         │              │  - Slack Bot    │ │
│         │              └─────────────────┘ │
│         │                      ↓           │
│         │              ┌─────────────────┐ │
│         │              │  Agent Runtime  │ │
│         │              └─────────────────┘ │
└─────────┼───────────────────────────────────┘
          │
          │ WebSocket 连接
          │
    ┌─────▼──────┐
    │  External  │
    │  Clients   │
    │ iOS/Web/CLI│
    └────────────┘
```

- **优点**: 统一管理，多客户端，易于监控
- **缺点**: 稍微复杂一点
- **适用**: 生产环境，多渠道支持

#### 模式 3: 纯 Gateway（高级）

```
Custom App → WebSocket → Gateway Server → Agent
```

- **优点**: 灵活，适合自定义应用
- **缺点**: 需要自己实现客户端协议
- **适用**: iOS/Android 应用，自定义集成

---

## TypeScript 官方实现

### 关键发现

查看官方 TypeScript 代码后，发现：

**Channels 不是 Gateway 的客户端，而是服务器端插件！**

### 代码分析

#### 1. Gateway Server 处理 Agent 请求

```typescript
// src/gateway/server-methods/agent.ts
export const agentHandlers: GatewayRequestHandlers = {
  agent: async ({ params, respond, context }) => {
    const message = request.message.trim();
    
    // 直接调用 agent 命令
    const result = await agentCommand({
      message,
      sessionKey,
      // ...
    });
    
    respond(true, result);
  }
};
```

#### 2. Channel 作为插件注册

```typescript
// src/gateway/server-methods/channels.ts
const plugins = listChannelPlugins();
const plugin = getChannelPlugin(channelId);

// 通过插件系统管理 channels
await context.stopChannel(channelId, accountId);
```

#### 3. Gateway 发送消息到 Channel

```typescript
// src/gateway/server-methods/send.ts
export const sendHandlers: GatewayRequestHandlers = {
  send: async ({ params, respond, context }) => {
    // 通过插件发送消息
    await deliverOutboundPayloads({
      channel: normalizeChannelId(request.channel),
      to: request.to,
      message: request.message
    });
  }
};
```

### 工作流程

1. **Telegram Bot** 收到用户消息
2. Bot 通过**内部方法调用**（不是 WebSocket）传递给 Agent
3. Agent 处理并返回响应
4. Bot 发送回 Telegram
5. **同时** Gateway 广播事件给所有连接的外部客户端

---

## Python 实现

### 核心组件

#### 1. 集成服务器类

```python
class IntegratedOpenClawServer:
    """
    集成服务器：Gateway + Channels + Agent 在同一进程
    """
    def __init__(self, config):
        # 核心组件
        self.session_manager = SessionManager(workspace)
        self.agent_runtime = AgentRuntime()
        self.channel_registry = ChannelRegistry()
        self.gateway_server = GatewayServer(config)
        
    async def setup_telegram(self, bot_token):
        """设置 Telegram 作为服务器端插件"""
        telegram = EnhancedTelegramChannel()
        
        # 设置消息处理器
        async def handle_message(message):
            # 通过 agent runtime 处理
            session = self.session_manager.get_session(f"telegram-{message.chat_id}")
            
            response = ""
            async for event in self.agent_runtime.run_turn(session, message.text):
                if event.type == "assistant":
                    response += event.data.get("delta", {}).get("text", "")
            
            # 发送回 Telegram
            await telegram.send_text(message.chat_id, response)
            
            # 广播到 Gateway 客户端
            await self.gateway_server.broadcast_event("chat", {
                "channel": "telegram",
                "message": message.text,
                "response": response
            })
        
        telegram.set_message_handler(handle_message)
        self.channel_registry.register(telegram)
        await telegram.start({"bot_token": bot_token})
```

#### 2. Gateway Server

```python
class GatewayServer:
    """WebSocket 服务器"""
    
    async def handle_connection(self, websocket):
        """处理新的 WebSocket 连接"""
        connection = GatewayConnection(websocket, self.config)
        
        async for message in websocket:
            await connection.handle_message(message)
    
    async def broadcast_event(self, event, payload):
        """广播事件给所有连接的客户端"""
        for connection in self.connections:
            await connection.send_event(event, payload)
```

---

## Telegram Bot 连接流程

### 详细步骤

#### 启动阶段

```python
# 1. 启动集成服务器
server = IntegratedOpenClawServer(config)

# 2. 设置 Telegram 插件
await server.setup_telegram(bot_token)
# 此时 Telegram bot 开始监听 Telegram API

# 3. 启动 Gateway 服务器
await server.gateway_server.start()
# Gateway 开始监听 ws://localhost:8765
```

#### 消息处理流程

```
1. 用户在 Telegram 发送消息
      ↓
2. Telegram Bot API 推送更新
      ↓
3. EnhancedTelegramChannel 收到消息
      ↓
4. 调用 handle_message() 处理器
      ↓
5. 通过 agent_runtime.run_turn() 处理
      ↓
6. Agent 返回响应
      ↓
7. 发送回 Telegram（通过 Bot API）
      ↓
8. 广播事件到 Gateway 客户端（可选）
```

### 关键点

1. **不需要 WebSocket 客户端**
   - Telegram Bot 直接在服务器进程中运行
   - 通过 Python 函数调用，不是网络请求

2. **Gateway 的作用**
   - 提供 WebSocket API 给**外部客户端**
   - Telegram Bot 本身不通过 Gateway 连接
   - Gateway 可以广播 Telegram 消息给其他客户端

3. **统一架构**
   - 所有 channels 都是插件
   - Gateway 提供统一的 RPC 接口
   - 外部客户端通过 Gateway 访问所有功能

---

## 完整示例

### 1. 启动集成服务器

```bash
# 设置环境变量
export TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
export ANTHROPIC_API_KEY=sk-ant-...

# 启动服务器
uv run python examples/10_gateway_telegram_bridge.py
```

### 2. 使用 Telegram

直接在 Telegram 中发送消息给你的 bot，即可对话。

### 3. 连接外部客户端（可选）

```javascript
// JavaScript 客户端示例
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
  // 连接握手
  ws.send(JSON.stringify({
    type: 'req',
    id: '1',
    method: 'connect',
    params: {
      maxProtocol: 1,
      client: {
        name: 'web-client',
        version: '1.0.0',
        platform: 'web'
      }
    }
  }));
};

ws.onmessage = (event) => {
  const frame = JSON.parse(event.data);
  
  if (frame.type === 'res' && frame.id === '1') {
    console.log('Connected!', frame.payload);
    
    // 发送消息到 agent
    ws.send(JSON.stringify({
      type: 'req',
      id: '2',
      method: 'agent',
      params: {
        message: 'Hello from web!',
        sessionId: 'web-session'
      }
    }));
  }
  
  if (frame.type === 'event' && frame.event === 'chat') {
    // 收到 Telegram 消息事件
    console.log('Telegram chat:', frame.payload);
  }
};
```

### 4. Python 客户端示例

```python
import asyncio
import json
import websockets

async def connect_to_gateway():
    async with websockets.connect('ws://localhost:8765') as ws:
        # 连接握手
        await ws.send(json.dumps({
            'type': 'req',
            'id': '1',
            'method': 'connect',
            'params': {
                'maxProtocol': 1,
                'client': {
                    'name': 'python-client',
                    'version': '1.0.0',
                    'platform': 'python'
                }
            }
        }))
        
        # 接收 hello 响应
        response = await ws.recv()
        hello = json.loads(response)
        print(f"Connected: {hello}")
        
        # 发送消息
        await ws.send(json.dumps({
            'type': 'req',
            'id': '2',
            'method': 'agent',
            'params': {
                'message': 'Hello from Python!',
                'sessionId': 'python-session'
            }
        }))
        
        # 监听事件
        while True:
            message = await ws.recv()
            frame = json.loads(message)
            print(f"Received: {frame}")

asyncio.run(connect_to_gateway())
```

---

## 🎯 总结

### 核心理解

1. **Telegram Bot 不是 Gateway 客户端**
   - 它是服务器端的 Channel 插件
   - 在同一个 Python 进程中运行

2. **Gateway 的真正用途**
   - 提供 WebSocket API 给外部应用
   - 统一管理所有 channels
   - 广播事件给多个客户端

3. **架构优势**
   - 📡 统一管理多个 channels
   - 🔌 支持多种客户端同时连接
   - 📊 集中监控所有对话
   - 🚀 生产级架构

### 下一步

- ✅ 使用 `examples/10_gateway_telegram_bridge.py` 启动服务器
- ✅ 通过 Telegram 测试对话功能
- ✅ 开发自定义 Gateway 客户端（可选）
- ✅ 添加更多 channels（Discord, Slack）

---

**🦞 OpenClaw Python - 连接你的 AI 到任何平台**
