# 🔄 重启 Gateway 并测试 PPT 功能

## 📋 已修复的问题

1. **`unknown_function` 错误** (Commit `3028710`)
   - 修复了 `sanitize_session_history` 丢失 `name` 字段的问题
   - 现在支持 snake_case 和 camelCase 字段

2. **Follow-up 工具循环** (Commit `67e7dc7`)
   - Follow-up call 现在传递空工具列表
   - 防止无限工具调用循环

3. **WebUI 协议** (Commit `13edd68`)
   - 恢复了 Gateway Protocol
   - WebUI 可以正常连接

## 🚀 重启步骤

### 1. 停止当前 Gateway

找到当前运行的终端，按 `Ctrl+C` 停止，或者：

```bash
pkill -f "uv run openclaw start"
```

### 2. 重新启动 Gateway

```bash
cd /Users/long/Desktop/ClawdBot2/openclaw-python
uv run openclaw start
```

### 3. 等待启动完成

看到以下日志表示启动成功：

```
✓ Gateway running on ws://127.0.0.1:18789
Press Ctrl+C to stop
```

## 🧪 测试 PPT 功能

### 方式 1: Telegram 测试

1. 打开 Telegram
2. 发送消息：**"帮我做个 PPT，主题是 OpenClaw 介绍"**
3. 观察日志和响应

### 方式 2: WebUI 测试

1. 打开浏览器访问 http://localhost:18789
2. 在聊天框输入：**"帮我做个 PPT，主题是 OpenClaw 介绍"**
3. 观察响应

## ✅ 预期行为

修复后的正确流程：

```
1. 用户: "帮我做个 PPT"
2. Agent: [调用工具 ppt_generate]
3. Tool Result: "✅ Created presentation: ..." (name="ppt_generate") ✅
4. Follow-up Call:
   - 日志显示: "🚫 Disabling tools for follow-up call"
   - 日志显示: "🔧 Received 0 tools from runtime"
   - Gemini 返回文本响应 ✅
5. Agent: "我已经为您创建了演示文稿..."
6. File Event: 发送 .pptx 文件到 Telegram
```

## 🔍 验证日志

### 关键日志标记

✅ **正确的日志：**
```
[telegram] Starting runtime.run_turn with N tools  (N > 0)
🔧 Received N tools from runtime  (初始调用)
🚫 Disabling tools for follow-up call  (follow-up)
🔧 Received 0 tools from runtime  (follow-up)
Tool message: name='ppt_generate'
[telegram] Sending generated file: ...
📎 [telegram] Sent file to ...
```

❌ **错误的日志（已修复）：**
```
function_response=unknown_function  ← 应该不再出现
office_ppt.doc_generate_ppt  ← 错误的工具名
No response text generated  ← 应该有文本响应
```

## 🐛 如果还有问题

### 1. 检查工具注册

```bash
cd openclaw-python
uv run python -c "
from openclaw.agents.tools.registry import ToolRegistry
from pathlib import Path
registry = ToolRegistry(workspace_dir=Path.home())
print('Registered tools:', len(registry.list_tools()))
for tool in registry.list_tools():
    print(f'  - {tool.name}: {tool.description[:60]}...')
"
```

### 2. 检查 python-pptx 依赖

```bash
uv pip list | grep pptx
```

如果没有安装：
```bash
uv pip install python-pptx
```

### 3. 清除旧的会话历史

如果有 `unknown_function` 残留：

```bash
# 备份旧会话
mv ~/.openclaw/agents/main/sessions ~/.openclaw/agents/main/sessions.backup

# 重启 Gateway
```

### 4. 查看完整日志

```bash
# 在运行 Gateway 的终端中，观察完整输出
# 特别注意：
# - 工具注册数量
# - 初始调用传递的工具数量
# - Follow-up call 的工具数量
# - 文件生成和发送的日志
```

## 📝 报告问题

如果测试后仍有问题，请提供：

1. **完整的日志片段**（从用户消息到响应结束）
2. **使用的命令**（Telegram 消息内容）
3. **观察到的行为**（收到什么响应，是否有文件）
4. **预期的行为**（应该怎样）

## 🎯 相关文件

- `openclaw/agents/tools/document_gen.py` - PPT 生成工具
- `openclaw/agents/tools/registry.py` - 工具注册
- `openclaw/gateway/channel_manager.py` - 文件发送逻辑
- `openclaw/agents/history_utils.py` - 历史消息处理（已修复）
- `openclaw/agents/runtime.py` - Follow-up call 逻辑（已修复）
