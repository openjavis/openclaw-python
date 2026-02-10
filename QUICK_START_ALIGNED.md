# 🚀 OpenClaw Python - 快速开始（对齐版本）

## 新功能速览

本版本已与TypeScript完全对齐，新增：

### 🎨 统一Browser系统
```python
from openclaw.browser import UnifiedBrowserTool
tool = UnifiedBrowserTool()
await tool.execute({"action": "navigate", "url": "https://example.com"})
```

### 💬 Auto-Reply系统
```python
from openclaw.auto_reply import dispatch_inbound_message
# 自动消息处理、命令检测、智能回复
```

### 🔍 Memory向量搜索
```python
from openclaw.memory import BuiltinMemoryManager
results = await manager.search("query", use_vector=True, use_hybrid=True)
```

### 🎤 多Provider TTS
```python
from openclaw.agents.tools.tts_providers import EdgeTTSProvider
# 免费Edge TTS，200+声音
```

### 📸 Media Understanding
```python
from openclaw.media_understanding import analyze_media
result = await analyze_media("image.jpg")
```

---

## 安装

```bash
# 核心依赖
pip install playwright openai anthropic google-generativeai
pip install watchdog websockets markdown edge-tts
pip install opencv-python sentence-transformers

# 安装playwright浏览器
playwright install
```

---

## 核心特性

✅ **Browser自动化** - 统一Playwright控制器  
✅ **Auto-Reply** - 完整消息处理系统  
✅ **Memory搜索** - 向量+FTS混合搜索  
✅ **Media分析** - 图像/音频/视频  
✅ **Multi-TTS** - 4个providers  
✅ **90+ Handlers** - 完整Gateway API  

---

详细文档: [`ALIGNMENT_COMPLETE.md`](./ALIGNMENT_COMPLETE.md)
