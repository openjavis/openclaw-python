# Gemini API 设置和使用指南

## ✅ 测试成功！

你的 Gemini API 已成功配置并测试通过。

---

## 📋 测试结果

### API 状态
- ✅ API Key 有效
- ✅ 30 个可用模型
- ✅ 中文对话正常
- ✅ 多轮对话正常
- ✅ 代码生成正常
- ✅ 流式输出正常

### 使用的模型
- **Gemini 2.5 Flash** (推荐) - 最新、快速
- **Gemini 2.5 Pro** - 最强大
- **Gemini 2.0 Flash** - 稳定版

---

## 🚀 快速开始

### 1. 基础对话

```python
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from openclaw.agents.providers.gemini_provider import GeminiProvider
from openclaw.agents.providers.base import LLMMessage

# 加载 .env
load_dotenv()

async def chat():
    provider = GeminiProvider(
        model="models/gemini-2.5-flash",  # 推荐使用
        api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    messages = [
        LLMMessage(role="user", content="你好！")
    ]
    
    async for response in provider.stream(messages):
        if response.type == "text_delta":
            print(response.content, end="", flush=True)

asyncio.run(chat())
```

### 2. 运行测试

```bash
# 运行成功的测试
uv run python test_gemini_success.py
```

---

## 📝 推荐模型

### 按用途选择

**日常对话（快速）：**
```python
model = "models/gemini-2.5-flash"      # 最新、最快
model = "models/gemini-flash-latest"   # 自动使用最新
```

**复杂任务（强大）：**
```python
model = "models/gemini-2.5-pro"        # 最强大
model = "models/gemini-pro-latest"     # 自动使用最新
```

**代码生成：**
```python
model = "models/gemini-2.5-flash"      # 推荐
```

**轻量级任务：**
```python
model = "models/gemini-2.0-flash-lite"  # 更快、更便宜
```

---

## 🔧 配置说明

### 环境变量（.env）

```bash
# Google Gemini API Key
GOOGLE_API_KEY=your-actual-key-here
```

### 重要提醒
- ✅ `.env` 文件已在 `.gitignore` 中
- ✅ 测试文件 `test_*.py` 已被忽略
- ⚠️ **永远不要提交 .env 到 GitHub**

---

## 💡 使用技巧

### 1. 多轮对话

```python
messages = []

# 第一轮
messages.append(LLMMessage(role="user", content="介绍下 Python"))
# ... 获取回复并添加到 messages

# 第二轮（带上下文）
messages.append(LLMMessage(role="assistant", content=reply))
messages.append(LLMMessage(role="user", content="给个例子"))
```

### 2. 系统提示

```python
messages = [
    LLMMessage(role="system", content="你是一个 Python 专家"),
    LLMMessage(role="user", content="如何使用 async/await?")
]
```

### 3. 控制输出

```python
async for response in provider.stream(
    messages,
    max_tokens=500,      # 限制长度
    temperature=0.7      # 控制创造性 (0-1)
):
    ...
```

---

## 🐛 常见问题

### Q: 404 错误 "model not found"
**A:** 必须使用 `models/` 前缀，例如：
```python
✅ "models/gemini-2.5-flash"
❌ "gemini-2.5-flash"
❌ "google/gemini-2.5-flash"
```

### Q: API Key 无效
**A:** 检查：
1. `.env` 文件中 `GOOGLE_API_KEY` 拼写正确
2. API Key 是否已启用 Gemini API
3. 访问 https://makersuite.google.com/app/apikey 确认

### Q: FutureWarning 警告
**A:** 这是正常的，旧的 `google.generativeai` 包已废弃。
可以忽略，或升级：
```bash
pip install google-genai
```

---

## 📊 性能参考

| 模型 | 速度 | 智能 | 成本 | 适用场景 |
|-----|------|------|------|---------|
| gemini-2.5-flash | ⚡⚡⚡ | ⭐⭐⭐ | $ | 日常对话 |
| gemini-2.5-pro | ⚡⚡ | ⭐⭐⭐⭐⭐ | $$$ | 复杂任务 |
| gemini-2.0-flash-lite | ⚡⚡⚡⚡ | ⭐⭐ | $ | 简单任务 |

---

## 🎯 下一步

1. **集成到 ClawdBot**
   - 使用 `AgentRuntime` 完整功能
   - 添加工具支持
   - 连接通讯渠道

2. **探索高级功能**
   - 多模态（图片、音频）
   - 函数调用
   - 上下文缓存

3. **生产部署**
   - 配置 API Key 轮换
   - 添加错误重试
   - 监控使用量

---

## 📚 相关文档

- [Gemini API 官方文档](https://ai.google.dev/docs)
- [ClawdBot 高级功能指南](docs/guides/ADVANCED_FEATURES.md)
- [v0.6.0 发布说明](RELEASE_NOTES_v0.6.0.md)

---

**测试时间**: 2026-01-31  
**测试状态**: ✅ 全部通过  
**ClawdBot 版本**: v0.6.0
