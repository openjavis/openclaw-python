# 📱 Telegram Bot 命令使用指南

## ✅ 已实现的斜杠命令

### 1. `/start` - 开始使用
启动 Bot 并显示欢迎信息。

**功能：**
- 介绍 AI 助手的核心能力
- 显示可用命令列表
- 提供使用示例

**示例响应：**
```
👋 欢迎使用 OpenClaw AI 助手！

✨ 我的能力：
• 💻 执行命令行操作
• 📁 读写文件
• 🌐 搜索网络信息
• 🖼️ 分析和生成图片
• 🎯 40+ 专业技能

📝 可用命令：
/help - 查看帮助信息
/status - 查看系统状态
...
```

---

### 2. `/help` - 获取帮助
显示详细的帮助文档。

**功能：**
- 核心功能说明
- 使用技巧
- 完整命令列表

**包含内容：**
- 命令执行能力
- 文件操作
- 网络功能
- 图片处理
- 专业技能

---

### 3. `/status` - 查看状态
显示当前系统状态和会话信息。

**显示信息：**
- Bot 运行状态
- 会话 ID
- 用户 ID
- 功能状态（工具、技能、记忆）
- 当前时间

**示例响应：**
```
📊 系统状态

🤖 Bot 信息：
• 状态: ✅ 运行中
• 频道: telegram
• 模型: Gemini Flash 3

💬 会话信息：
• 会话 ID: telegram-12345
• 用户 ID: 67890

⚡ 功能状态：
• 工具: ✅ 19个已加载
• 技能: ✅ 40个可用
...
```

---

### 4. `/reset` - 重置对话
清除对话历史，重新开始会话。

**功能：**
- 删除当前会话的所有消息
- 保留系统设置
- 开始新的对话

**使用场景：**
- 想从头开始新话题
- 对话历史过长
- 上下文混乱

---

### 5. `/revoke` - 清除数据
完全删除所有会话数据（符合 GDPR）。

**删除内容：**
- ✅ 对话历史
- ✅ 会话状态
- ✅ 临时缓存

**隐私保护：**
- 数据从系统中完全移除
- 不会保留任何对话记录
- 可以随时重新开始使用

---

## 🧪 测试命令

在 Telegram 中依次输入以下命令测试：

```
/start
/help
/status
你好，你能做什么？
/reset
你好（这次是新会话）
/revoke
```

---

## 🔧 技术实现

### 命令处理器注册
```python
# enhanced_telegram.py
self._app.add_handler(CommandHandler("start", self._handle_start_command))
self._app.add_handler(CommandHandler("help", self._handle_help_command))
self._app.add_handler(CommandHandler("status", self._handle_status_command))
self._app.add_handler(CommandHandler("reset", self._handle_reset_command))
self._app.add_handler(CommandHandler("revoke", self._handle_revoke_command))
```

### 命令与普通消息的区分
- 命令：以 `/` 开头，由 `CommandHandler` 处理
- 普通消息：由 `MessageHandler` 处理，会传递给 AI Agent

---

## 📋 未来可添加的命令

### 建议命令：
- `/tools` - 查看可用工具列表
- `/skills` - 查看可用技能列表
- `/history` - 查看对话历史摘要
- `/export` - 导出对话记录
- `/settings` - 配置个人偏好
- `/language` - 切换语言
- `/model` - 切换 AI 模型

---

## 🎯 最佳实践

### 命令使用建议：
1. **首次使用**：发送 `/start` 了解功能
2. **需要帮助**：发送 `/help` 查看文档
3. **检查状态**：发送 `/status` 确认系统正常
4. **重新开始**：发送 `/reset` 清除历史
5. **保护隐私**：发送 `/revoke` 删除数据

### 命令与对话：
- 命令用于**系统操作**（查看状态、重置等）
- 普通消息用于**AI 对话**（提问、任务等）
- 可以混合使用

---

## 📝 日志示例

当用户执行命令时，日志会显示：

```
2026-02-05 06:20:45 | INFO | [telegram] User 12345 started bot
2026-02-05 06:21:30 | INFO | [telegram] User 12345 requested help
2026-02-05 06:22:15 | INFO | [telegram] User 12345 checked status
2026-02-05 06:23:00 | INFO | [telegram] User 12345 reset conversation
2026-02-05 06:24:30 | INFO | [telegram] User 12345 revoked data
```

---

## ✨ 完成状态

- ✅ `/start` - 欢迎信息
- ✅ `/help` - 帮助文档
- ✅ `/status` - 系统状态
- ✅ `/reset` - 重置对话
- ✅ `/revoke` - 清除数据
- ✅ 命令处理器已注册
- ✅ 与 AI 对话分离
- ✅ 日志记录完整

**所有斜杠命令功能已完全实现！** 🚀
