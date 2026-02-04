# 🦞 OpenClaw Python - 完整功能指南

## 🎯 完整功能启动

现在你可以启动包含**所有功能**的 OpenClaw 服务器！

### 快速启动

```bash
cd /Users/openbot/Desktop/openclaw-python

# 方式 1: 使用启动脚本（推荐）
./start_with_all_features.sh

# 方式 2: 直接运行
uv run python start_full_featured.py

# 方式 3: 后台运行
./start_with_all_features.sh bg
```

---

## ✨ 包含的功能

### 1. 🔧 所有内置工具 (24+ Tools)

#### 文件操作
- `read_file` - 读取文件
- `write_file` - 写入文件
- `edit_file` - 编辑文件

#### 系统执行
- `bash` - 执行 Shell 命令
- `process` - 进程管理

#### Web 工具
- `web_fetch` - 获取网页内容
- `web_search` - 网页搜索

#### 浏览器自动化
- `browser` - 浏览器控制（Playwright）
  - 打开网页
  - 点击元素
  - 截图
  - 表单填写
  - JavaScript 执行

#### 多媒体
- `image` - 图像分析
- `tts` - 文字转语音
- `voice_call` - 语音通话

#### 定时任务
- `cron` - 定时任务调度

#### 会话管理
- `sessions_list` - 列出所有会话
- `sessions_history` - 查看历史
- `sessions_send` - 跨会话发送消息
- `sessions_spawn` - 创建新会话

#### 频道操作
- `message` - 发送消息到频道
- `telegram_actions` - Telegram 操作
- `discord_actions` - Discord 操作
- `slack_actions` - Slack 操作
- `whatsapp_actions` - WhatsApp 操作

#### 高级功能
- `nodes` - 节点管理
- `canvas` - Canvas 画板
- `patch` - 代码补丁应用

### 2. 🎯 所有技能 (50+ Skills)

#### 生产力工具
- `obsidian` - Obsidian 笔记
- `notion` - Notion 管理
- `apple-notes` - Apple 备忘录
- `apple-reminders` - Apple 提醒事项
- `bear-notes` - Bear 笔记
- `things-mac` - Things 任务管理
- `trello` - Trello 看板

#### 开发工具
- `github` - GitHub 集成
- `coding-agent` - 代码助手
- `skill-creator` - 技能创建器

#### 通信工具
- `bluebubbles` - iMessage (BlueBubbles)
- `imsg` - iMessage
- `discord-adv` - Discord 高级功能
- `slack` - Slack 集成
- `himalaya` - Email (Himalaya)

#### AI 工具
- `gemini` - Google Gemini
- `openai-image-gen` - OpenAI 图像生成
- `openai-whisper` - OpenAI 语音识别
- `sherpa-onnx-tts` - TTS 引擎

#### 智能家居
- `openhue` - Philips Hue 灯光控制
- `sonoscli` - Sonos 音响控制

#### 媒体工具
- `spotify-player` - Spotify 播放器
- `video-frames` - 视频帧提取
- `gifgrep` - GIF 搜索
- `songsee` - 音乐识别

#### 工具集成
- `1password` - 1Password 密码管理
- `goplaces` - 地点搜索
- `local-places` - 本地地点
- `weather` - 天气查询
- `web-search` - 网页搜索
- `food-order` - 食物订购
- `ordercli` - 订单命令行

#### 服务器管理
- `tmux` - Tmux 会话管理
- `mcporter` - Minecraft 服务器
- `eightctl` - 服务控制

#### 其他
- `summarize` - 文本摘要
- `session-logs` - 会话日志
- `model-usage` - 模型使用统计
- `oracle` - Oracle 数据库
- `blogwatcher` - 博客监控
- `bird` - Bird 工具
- `camsnap` - 摄像头快照
- `clawdhub` - ClawdHub 集成
- `gog` - GOG 游戏平台
- `nano-banana-pro` - Nano Banana Pro
- `nano-pdf` - PDF 处理
- `peekaboo` - Peekaboo 工具
- `sag` - SAG 工具
- `wacli` - WA CLI

### 3. 🧠 完整 Memory 管理

#### 自动功能
- ✅ **自动保存** - 所有对话自动保存到磁盘
- ✅ **智能压缩** - 对话过长时自动压缩
- ✅ **重要消息保留** - KEEP_IMPORTANT 策略
- ✅ **无限历史** - 不限制消息数量
- ✅ **跨会话** - 支持多个独立会话

#### 技术特性
- **Session Persistence**: 
  - 位置: `./workspace/.sessions/`
  - 格式: JSON
  - 自动加载/保存

- **Context Management**:
  - 自动检测 token 数量
  - 达到阈值自动压缩
  - 保留重要消息和工具调用

- **Compaction Strategy**:
  - `KEEP_IMPORTANT` - 保留重要消息
  - `KEEP_RECENT` - 保留最近消息  
  - `SUMMARIZE` - 摘要旧消息（未来）

#### 使用示例

```python
# 自动管理，无需手动操作
# 1. 消息自动保存
user: "你好"
assistant: "你好！..." # ✅ 自动保存

# 2. 对话过长时自动压缩
# 当 token 数超过 80% 时：
# - 自动压缩到 70%
# - 保留最近的消息
# - 保留工具调用历史
# - 保留重要上下文

# 3. 跨会话记忆
# 每个频道/用户有独立会话
# Telegram 用户 123 -> session: telegram-123
# Discord 用户 456 -> session: discord-456
```

### 4. 🌐 Gateway + WebSocket

#### 功能
- **Channel Manager** - 统一管理所有频道
- **WebSocket API** - `ws://localhost:8765`
- **Event Broadcasting** - 实时事件广播
- **Multi-Channel** - 同时运行多个频道

#### API 方法
- `connect` - 连接握手
- `agent` - 发送消息给 AI
- `send` - 发送到频道
- `channels.list` - 列出频道
- `channels.start/stop` - 控制频道
- `sessions.list` - 列出会话

---

## 📊 功能对比

### 当前简单 Bot vs 完整功能服务器

| 功能 | 简单 Bot | 完整功能服务器 |
|-----|---------|---------------|
| Tools | ❌ 无 | ✅ 24+ 工具 |
| Skills | ❌ 无 | ✅ 50+ 技能 |
| Memory 管理 | ⚠️ 基础 | ✅ 完整（自动压缩） |
| Context 管理 | ❌ 无 | ✅ 智能管理 |
| 对话历史 | ⚠️ 有限 | ✅ 无限（自动压缩） |
| WebSocket API | ❌ 无 | ✅ 有 |
| 多频道 | ❌ 单一 | ✅ 支持 |
| 事件广播 | ❌ 无 | ✅ 有 |
| 浏览器自动化 | ❌ 无 | ✅ 有 |
| 跨会话通信 | ❌ 无 | ✅ 有 |

---

## 🚀 启动步骤

### 1. 停止当前简单 Bot

```bash
pkill -f "05_telegram_bot"
```

### 2. 启动完整功能服务器

```bash
cd /Users/openbot/Desktop/openclaw-python
./start_with_all_features.sh
```

### 3. 测试所有功能

在 Telegram 中测试：

#### 测试文件操作
```
请读取当前目录的 README.md 文件
```

#### 测试 Web 搜索
```
帮我搜索一下 Python 3.12 的新特性
```

#### 测试浏览器
```
打开 https://www.google.com 并截图
```

#### 测试代码执行
```
运行命令 ls -la 并告诉我结果
```

#### 测试多轮对话
```
第1轮: 我叫张三
第2轮: 我的名字是什么？（应该记得）
第10轮: 我们最开始聊了什么？（应该记得）
```

---

## 💡 使用技巧

### 1. Agent 会自动选择工具

你不需要告诉 Agent 用什么工具，它会自动选择：

- "读取文件" → 自动使用 `read_file`
- "搜索..." → 自动使用 `web_search`
- "打开网页" → 自动使用 `browser`
- "运行命令" → 自动使用 `bash`

### 2. 对话历史自动管理

- 无需担心对话过长
- 自动压缩保留重要内容
- 所有历史都持久化保存

### 3. 跨会话通信

```
# 在 Telegram 中
"列出所有会话"  # 使用 sessions_list 工具

"向 session-abc 发送消息：你好"  # 使用 sessions_send 工具
```

### 4. 使用 Skills

Skills 会自动加载到系统提示中，Agent 知道如何使用：

```
"帮我在 GitHub 上创建一个 issue"  # 使用 github skill
"在 Notion 中添加一个任务"  # 使用 notion skill
"控制 Hue 灯光，打开客厅的灯"  # 使用 openhue skill
```

---

## 🔧 配置说明

### 环境变量 (.env)

```bash
# LLM API（必需）
GOOGLE_API_KEY=your-key  # ✅ 已配置

# 频道（可选）
TELEGRAM_BOT_TOKEN=your-token  # ✅ 已配置
DISCORD_BOT_TOKEN=your-token   # 可选
SLACK_BOT_TOKEN=your-token     # 可选

# Skills 相关（部分 skills 需要）
GITHUB_TOKEN=...
NOTION_API_KEY=...
SPOTIFY_CLIENT_ID=...
# ... 等等
```

### 代码配置

编辑 `start_full_featured.py`:

```python
# Agent 配置
runtime = AgentRuntime(
    model="gemini/gemini-3-flash-preview",
    enable_context_management=True,  # Context 管理
    thinking_mode="OFF",              # 思考模式: OFF/LOW/MEDIUM/HIGH
    compaction_strategy="KEEP_IMPORTANT",  # 压缩策略
)
```

---

## 📊 监控和调试

### 查看日志

```bash
# 后台运行时
tail -f /tmp/openclaw_full.log

# 或前台运行直接看输出
```

### 查看会话

```bash
# 会话文件位置
ls -la ./workspace/.sessions/

# 查看特定会话
cat ./workspace/.sessions/telegram-123456.json
```

### 工具使用统计

Agent 运行时会自动记录工具使用情况，在日志中可以看到：
- 工具调用次数
- 成功率
- 平均执行时间

---

## 🎯 最佳实践

### 1. 让 Agent 自主选择

❌ 不好:
```
"使用 web_search 工具搜索 Python 教程"
```

✅ 好:
```
"帮我找一下 Python 教程"
```

### 2. 明确需求

✅ 好:
```
"读取 config.json 文件，找到 database 配置，告诉我连接字符串"
```

### 3. 利用 Memory

✅ 好:
```
第1轮: "我正在开发一个 Web 应用"
第2轮: "用什么技术栈好？"（记得上下文）
第3轮: "帮我搭建项目结构"（记得之前的讨论）
```

### 4. 组合多个工具

✅ 好:
```
"搜索 FastAPI 教程，找到官方文档，打开并截图首页"
```
→ 会自动使用: `web_search` + `browser`

---

## 🆘 故障排查

### 问题 1: 启动失败

```bash
# 检查日志
tail -50 /tmp/openclaw_full.log

# 检查 API Key
grep "GOOGLE_API_KEY" .env
```

### 问题 2: 工具无法使用

某些工具需要额外依赖：
- `browser` - 需要 Playwright: `uv run python -m playwright install chromium`
- `tts` - 需要音频库
- `image` - 需要图像处理库

### 问题 3: Skill 不可用

查看日志中的 "Skills eligible" 信息，某些 skills 需要：
- 特定操作系统
- 额外的二进制文件
- 环境变量配置

---

## 🔗 相关文档

- **完整架构**: `START_FULL_FEATURED.md`
- **Gateway 文档**: `README.md` (Gateway Protocol 部分)
- **Tools 文档**: `openclaw/agents/tools/`
- **Skills 文档**: `skills/*/SKILL.md`

---

## 🎉 总结

现在你有一个**功能完整**的 AI Agent：

✅ **24+ 工具** - 可以执行各种操作  
✅ **50+ 技能** - 可以集成各种服务  
✅ **智能 Memory** - 自动管理对话历史  
✅ **完整 Context** - 无限对话不丢失上下文  
✅ **Gateway API** - 支持多客户端和实时通信  
✅ **生产就绪** - 可扩展的架构

**一键启动:**
```bash
./start_with_all_features.sh
```

享受完整功能的 AI Agent！🦞✨
