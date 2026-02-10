# 安装步骤 - 确保所有新功能可用

## 1. 安装新依赖

```bash
cd openclaw-python

# 安装新增的依赖
uv sync

# 或者手动安装
uv pip install reportlab>=4.0.0
```

## 2. 验证依赖

```bash
# 检查是否安装成功
python -c "import apscheduler; print('✅ APScheduler:', apscheduler.__version__)"
python -c "import pptx; print('✅ python-pptx:', pptx.__version__)"
python -c "import reportlab; print('✅ reportlab:', reportlab.__version__)"
python -c "import telegram; print('✅ python-telegram-bot:', telegram.__version__)"
```

预期输出：
```
✅ APScheduler: 3.10.x
✅ python-pptx: 0.6.23
✅ reportlab: 4.x.x
✅ python-telegram-bot: 21.x
```

## 3. 重启 Gateway

```bash
# 使用快速重启脚本
./quick_restart.sh

# 或手动重启
pkill -f "openclaw start"
openclaw start
```

## 4. 测试功能

### A. 测试 Cron（定时任务）

在 Telegram 发送：
```
设置一个测试提醒，1 分钟后提醒我
```

或：
```
Set a reminder for 1 minute from now
```

或更具体：
```
明天早上 7 点提醒我查看股市新闻
```

**预期行为：**
- Bot 应该回复："✅ 已创建定时任务..."
- 到时间后，Bot 会自动发送提醒消息

### B. 测试 PPT 生成

在 Telegram 发送：
```
创建一个关于人工智能的演示文稿，包含 3 张幻灯片
```

或：
```
Generate a presentation about Python programming with 5 slides
```

**预期行为：**
- Bot 生成 .pptx 文件
- Bot 发送文件到 Telegram
- 你可以下载并打开查看

### C. 测试 PDF 生成

在 Telegram 发送：
```
生成一个 PDF 报告，内容是今天的任务总结
```

**预期行为：**
- Bot 生成 .pdf 文件
- Bot 可以发送文件或告诉你文件位置

### D. 测试文件接收

在 Telegram：
1. 发送一张图片给 Bot
2. Bot 应该能接收并分析/处理

**预期行为：**
- Bot 回复："我收到了一张图片..."
- Bot 可以分析图片内容

### E. 测试 Web UI

打开浏览器访问：
```
http://127.0.0.1:8080
```

**预期行为：**
- 看到美观的深色主题界面
- 显示 "Connected" 状态
- 可以发送消息并收到回复
- 侧边栏显示系统信息

## 5. 常见问题

### 问题 1: Bot 说"无法直接控制硬件设备"

**原因：** 旧代码还在缓存中

**解决：**
```bash
# 清理缓存
find openclaw -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find openclaw -name "*.pyc" -delete

# 重启
./quick_restart.sh
```

### 问题 2: 找不到模块 (ImportError)

**解决：**
```bash
# 确保在正确的环境
cd openclaw-python

# 重新同步依赖
uv sync

# 验证安装
openclaw doctor
```

### 问题 3: Cron 任务创建但不触发

**检查：**
1. 确保 Gateway 一直在运行（不要关闭）
2. 查看日志：
```bash
# 在另一个终端查看日志
tail -f ~/.openclaw/logs/openclaw.log
```

### 问题 4: 文件生成但无法发送

**检查：**
1. 文件路径：应该在 `~/.openclaw/workspace/presentations/` 或 `/documents/`
2. Telegram bot 权限：确保 bot 有发送文件权限

## 6. 验证完整流程

### 完整测试场景：

```
User: 你好！显示你所有的能力
Bot: [列出所有工具，包括 cron, ppt_generate, pdf_generate, message 等]

User: 创建一个关于 AI 的演示文稿并发给我
Bot: ✅ 已创建演示文稿: AI_Introduction_20260209.pptx
     [发送文件]

User: 每天早上 9 点给我发送一条新闻摘要
Bot: ✅ 已设置定时任务 'daily-news-9am'
     我会在每天早上 9:00 为您发送新闻摘要。

[第二天早上 9:00]
Bot: ⏰ **提醒**
     
     这是您订阅的每日新闻摘要...

User: 查看我的所有定时任务
Bot: 已安排的任务 (1):
     - daily-news-9am
       计划: 每天 9:00 AM
       运行次数: 1
```

## 7. 目录结构确认

确保以下文件存在：

```
openclaw-python/
├── openclaw/
│   ├── agents/tools/
│   │   ├── cron.py            ✅ (更新)
│   │   ├── document_gen.py    ✅ (新增)
│   │   ├── channel_actions.py ✅ (已有)
│   │   └── registry.py        ✅ (更新)
│   ├── channels/
│   │   └── telegram.py        ✅ (已有文件传输)
│   └── web/static/control-ui/
│       └── index.html         ✅ (新 UI)
├── pyproject.toml             ✅ (更新依赖)
├── quick_restart.sh           ✅
└── NEW_FEATURES.md            ✅ (功能文档)
```

## 8. 成功标志

如果看到以下现象，说明一切正常：

- ✅ `openclaw start` 启动无错误
- ✅ Telegram bot 响应消息
- ✅ Web UI (localhost:8080) 可访问
- ✅ Bot 能理解定时任务请求
- ✅ Bot 能生成 PPT/PDF
- ✅ Bot 能接收和发送文件
- ✅ 日志中无报错

---

**现在运行 `./quick_restart.sh` 并开始测试！** 🚀
