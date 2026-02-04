# 🚀 Agent 改进计划

## 当前系统不足分析

### ❌ 1. Skills 没有生效
**问题**: Skills 被加载但从未传递给 LLM
**影响**: 50个预定义能力完全浪费
**优先级**: 🔴 高

### ❌ 2. 工具调用受限
**问题**: 只支持单轮工具调用，无法 tool chaining
**影响**: 无法完成复杂多步骤任务
**优先级**: 🔴 高

### ❌ 3. 长期记忆缺失
**问题**: 没有跨会话的知识库和用户偏好记忆
**影响**: Agent 每次都是"失忆"状态
**优先级**: 🟡 中

### ❌ 4. Context 管理简单
**问题**: 压缩策略不够智能，缺少语义检索
**影响**: 对话质量下降
**优先级**: 🟡 中

---

## 🎯 改进方案

### 阶段 1: 立即改进（1-2小时）

#### 1.1 启用 Skills 系统提示
**修改文件**: `openclaw/agents/runtime.py`, `openclaw/gateway/channel_manager.py`

```python
# 1. 在 runtime.py 添加 system_prompt 参数
async def run_turn(
    self,
    session: Session,
    message: str,
    tools: list[AgentTool] | None = None,
    images: list[str] | None = None,
    system_prompt: str | None = None,  # 新增
) -> AsyncIterator[AgentEvent]:
    # 如果有 system_prompt，添加到消息开头
    if system_prompt and not session.messages:
        session.add_system_message(system_prompt)
```

```python
# 2. 在 channel_manager.py 传递 skills_prompt
async for event in runtime.run_turn(
    session, 
    message.text, 
    tools=self.tools, 
    images=images,
    system_prompt=self.skills_prompt  # 新增
):
```

**效果**: Skills 立即生效，Agent 知道自己的能力

---

#### 1.2 支持多轮工具调用（Tool Chaining）
**修改文件**: `openclaw/agents/runtime.py`

**当前问题**:
```python
# 第二次调用时禁用工具
async for response in self.provider.stream(
    messages=llm_messages, tools=None, max_tokens=max_tokens
)
```

**改进方案**:
```python
# 添加 max_tool_rounds 参数
MAX_TOOL_ROUNDS = 5  # 最多5轮工具调用

current_round = 0
while current_round < MAX_TOOL_ROUNDS:
    # 始终提供工具
    async for response in self.provider.stream(
        messages=llm_messages, 
        tools=tools_param,  # 不再设为 None
        max_tokens=max_tokens
    ):
        if response.type == "tool_call":
            # 执行工具
            current_round += 1
            needs_continuation = True
        elif response.type == "done":
            if not tool_calls:
                # 没有工具调用，正常结束
                break
    
    if not needs_continuation:
        break
```

**效果**: 
- 支持多轮工具调用
- 可以实现复杂的任务链
- 例如: 搜索 → 分析 → 总结 → 保存

---

### 阶段 2: 中期改进（1-2天）

#### 2.1 启用长期记忆（LanceDB）
**修改文件**: `openclaw/agents/tools/registry.py`, `extensions/memory-lancedb/plugin.py`

**步骤**:
1. 解除 `lancedb` 和 `torch` 的注释（或寻找兼容版本）
2. 添加 `memory_search` 工具到工具注册表
3. 自动索引所有对话
4. 提供语义搜索历史对话的能力

**代码框架**:
```python
# 在每次对话后自动存储到向量数据库
async def _save_to_memory(session_id: str, message: str, response: str):
    # 使用 sentence-transformers 生成向量
    vector = encoder.encode(f"{message} {response}")
    
    # 存储到 LanceDB
    memory_table.add({
        "text": f"User: {message}\nAssistant: {response}",
        "vector": vector,
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    })
```

**效果**:
- 跨会话记忆
- 可以问"我之前问过什么？"
- 可以搜索历史知识

---

#### 2.2 智能 Context 管理
**功能**:
- 自动总结长对话
- 提取关键信息
- 语义检索相关历史

**实现**:
```python
async def intelligent_compaction(session: Session) -> Session:
    """智能压缩策略"""
    
    # 1. 提取关键信息
    key_facts = await extract_key_facts(session.messages)
    
    # 2. 生成对话总结
    summary = await generate_summary(session.messages)
    
    # 3. 保留最近的 N 条消息
    recent = session.messages[-10:]
    
    # 4. 重建 session
    new_session = Session(session.session_id, session.workspace_dir)
    new_session.add_system_message(f"Previous conversation summary:\n{summary}\n\nKey facts:\n{key_facts}")
    for msg in recent:
        new_session.messages.append(msg)
    
    return new_session
```

---

### 阶段 3: 高级改进（1周+）

#### 3.1 Agentic RAG（检索增强生成）
- 集成知识库（文档、网页）
- 自动判断何时检索
- 引用来源

#### 3.2 Multi-Agent 协作
- 专家 Agents（编码、研究、写作）
- Agent 之间通信
- 任务分配和协调

#### 3.3 工具自动发现和学习
- Agent 自己学习新工具
- 工具使用模式优化
- 个性化工具推荐

---

## 🔧 快速修复清单

### 今天就可以做：

1. ✅ **修复 Skills 集成**
   - [ ] 修改 `runtime.py` 添加 `system_prompt` 参数
   - [ ] 修改 `channel_manager.py` 传递 skills
   - [ ] 修改 `start_full_featured.py` 传递 skills_prompt 到 ChannelManager

2. ✅ **改进工具调用**
   - [ ] 修改 `runtime.py` 支持多轮工具调用
   - [ ] 添加 `max_tool_rounds` 配置
   - [ ] 测试 tool chaining

3. ✅ **优化日志**
   - [ ] 添加工具调用轮次日志
   - [ ] 显示 skills 加载状态
   - [ ] 记录长期记忆访问

---

## 📈 预期效果

### 修复 Skills 后：
```
用户: "我想开发一个 Python 项目"
Agent: [看到 coding-agent skill]
      "我可以帮你！我有编码助手能力，可以：
      1. 创建项目结构
      2. 编写代码
      3. 运行测试
      让我开始..."
```

### 多轮工具调用后：
```
用户: "研究一下 OpenAI 的最新产品并整理成报告"
Agent: 
  Round 1: [调用 web_search] 搜索 OpenAI 最新产品
  Round 2: [调用 web_fetch] 获取详细信息
  Round 3: [调用 write_file] 保存报告
  "已完成！报告已保存到 openai_report.md"
```

### 长期记忆后：
```
用户: "上次我们讨论的那个项目进展如何？"
Agent: [检索历史记忆]
      "你是说上周讨论的 Python 爬虫项目吗？
      我记得你想爬取新闻网站，已经完成了基础代码..."
```

---

## 🎯 下一步行动

你想要：
1. **立即修复** Skills 和工具调用？（推荐）
2. **规划** 长期记忆系统？
3. **测试** 当前系统的极限？

选择一个方向，我们开始实施！🚀
