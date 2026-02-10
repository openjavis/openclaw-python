# 快速测试指南

## 🚀 立即重启并测试！

### Step 1: 重启系统

```bash
cd /Users/openjavis/Desktop/xopen/openclaw-python
./quick_restart.sh
```

### Step 2: 在 Telegram 测试

打开 Telegram，找到你的 bot，发送以下消息：

#### 测试 1: 显示能力
```
你好！显示你所有的工具和能力
```

**预期：** Bot 列出 24+ 个工具，包括 cron, ppt_generate, pdf_generate, message 等

#### 测试 2: Cron 定时任务
```
设置一个 1 分钟后的测试提醒
```

**预期：** 
- Bot 立即回复："✅ 已创建定时任务..."（而不是说"无法控制硬件"）
- 1 分钟后收到提醒消息

#### 测试 3: PPT 生成
```
创建一个关于人工智能的演示文稿，包含 3 张幻灯片：介绍、应用、未来
```

**预期：**
- Bot 生成 .pptx 文件
- Bot 发送文件给你（或告诉你文件路径）

#### 测试 4: 文件接收
```
[发送一张图片给 Bot]
```

**预期：**
- Bot 回复："我收到了一张图片..."
- Bot 可以描述图片内容

#### 测试 5: 完整流程
```
创建一个关于 Python 编程的 PPT 并发给我
```

**预期：**
- Bot 生成 PPT
- Bot 通过 Telegram 发送文件
- 你收到 .pptx 文件

### Step 3: 在 Web UI 测试

打开浏览器：
```
http://127.0.0.1:8080
```

**预期：**
- 美观的深色主题界面
- 状态显示 "Connected" （绿色指示灯）
- 侧边栏显示 Model: google/gemini-3-pro-preview
- 可以发送消息并收到回复

尝试快捷操作：
- 点击 "⏰ Show Cron Jobs"
- 点击 "📊 Generate PPT"

### Step 4: 查看日志

如果有问题，查看日志：
```bash
tail -f ~/.openclaw/logs/openclaw.log
```

或查看终端输出。

## ✅ 成功标志

- [ ] Bot 不再说"无法控制硬件设备"
- [ ] Bot 能成功创建定时任务
- [ ] Bot 能生成 PPT 和 PDF
- [ ] Bot 能接收和发送文件
- [ ] Web UI 显示正常且功能完整
- [ ] 所有工具都可用

## 🐛 如果有问题

### 问题：Bot 还是说"无法控制硬件"

```bash
# 清理 Python 缓存
find openclaw -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find openclaw -name "*.pyc" -delete

# 强制重启
./quick_restart.sh
```

### 问题：缺少依赖

```bash
# 重新同步依赖
uv sync

# 验证安装
python -c "import reportlab; print('✅ reportlab OK')"
```

### 问题：端口被占用

```bash
# 查找并杀死进程
lsof -ti:18789 | xargs kill -9
lsof -ti:8080 | xargs kill -9

# 重启
openclaw start
```

## 📊 完整测试对话示例

```
用户: 你好！你能做什么？
Bot: 我是你的 AI 助手！我可以帮你：
     - 设置定时任务和提醒
     - 生成 PowerPoint 演示文稿
     - 创建 PDF 文档
     - 搜索网络信息
     - 执行文件操作
     - 分析图片
     ... [列出所有工具]

用户: 每天早上 7 点提醒我查看股市新闻
Bot: ✅ 已为您创建定时任务 'daily-stock-news-7am'
     我会在每天早上 7:00 为您发送股市新闻提醒。

用户: 创建一个关于 Python 的 PPT
Bot: 好的，我来为您创建一个关于 Python 的演示文稿...
     
     ✅ 已创建演示文稿: Python_Programming_20260209_141523.pptx
     路径: /Users/openjavis/.openclaw/workspace/presentations/...
     幻灯片数: 5
     
     [发送文件]

用户: [收到 .pptx 文件]
```

---

## 🎉 开始测试吧！

运行重启脚本，然后按照上面的步骤测试所有新功能！
