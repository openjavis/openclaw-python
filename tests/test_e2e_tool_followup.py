#!/usr/bin/env python3
"""端到端测试：工具调用和 follow-up 响应的完整流程"""

import asyncio
import os
import sys
from pathlib import Path

# 确保可以导入 openclaw
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.agents.runtime import MultiProviderRuntime
from openclaw.agents.session import Session
from openclaw.agents.tools.base import SimpleTool
import tempfile


def create_test_tool():
    """创建一个简单的测试工具"""
    def test_execute(**kwargs):
        return "Tool executed successfully!"
    
    return SimpleTool(
        name="test_tool",
        description="A test tool that always succeeds",
        parameters={
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Test input"
                }
            },
            "required": []
        },
        execute=test_execute
    )


async def test_tool_followup_flow():
    """测试完整的工具调用和 follow-up 流程"""
    
    # 检查是否有 API key
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  跳过测试：未设置 GEMINI_API_KEY")
        return
    
    print("=" * 60)
    print("端到端测试：工具调用 + Follow-up 响应")
    print("=" * 60)
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        
        # 创建会话
        session = Session(
            session_id="test-e2e-001",
            workspace_dir=workspace,
            session_key="test-e2e-001"
        )
        
        # 创建 runtime
        runtime = MultiProviderRuntime(
            provider_name="gemini",
            model_id="gemini-2.0-flash-exp",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        
        # 创建测试工具
        test_tool = create_test_tool()
        
        print("步骤 1: 发送需要工具的用户消息")
        print("-" * 60)
        session.add_user_message("Please use the test_tool with input 'hello'")
        
        # 运行 agent
        print("\n步骤 2: Agent 运行（应该调用工具）")
        print("-" * 60)
        
        events_collected = []
        tool_calls_count = 0
        text_responses = []
        unknown_function_found = False
        
        try:
            async for event in runtime.run(
                session=session,
                user_message=None,  # Already added to session
                tools=[test_tool],
                max_tokens=1000
            ):
                events_collected.append(event)
                
                if event.type == "tool_result":
                    tool_calls_count += 1
                    print(f"  ✅ 工具调用: {event.data.get('tool')}")
                    
                elif event.type == "text":
                    text = event.data.get("text", "")
                    text_responses.append(text)
                    if text.strip():
                        print(f"  💬 文本响应: {text[:100]}")
                    
                    # 检查是否有 unknown_function
                    if "unknown_function" in text.lower():
                        unknown_function_found = True
                        print(f"  ❌ 发现 unknown_function！")
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print()
        print("步骤 3: 验证结果")
        print("-" * 60)
        
        # 检查结果
        all_messages = session.get_messages()
        
        print(f"✅ 收集了 {len(events_collected)} 个事件")
        print(f"✅ 调用了 {tool_calls_count} 次工具")
        print(f"✅ 生成了 {len(text_responses)} 段文本")
        print(f"✅ 会话中有 {len(all_messages)} 条消息")
        print()
        
        # 验证工具消息有 name 字段
        tool_messages = [m for m in all_messages if m.role == "tool"]
        if tool_messages:
            print("检查工具消息的 name 字段：")
            for i, msg in enumerate(tool_messages):
                if msg.name:
                    print(f"  ✅ 工具消息 {i}: name='{msg.name}'")
                else:
                    print(f"  ❌ 工具消息 {i}: name 字段丢失！")
        print()
        
        # 最终判断
        success = True
        if tool_calls_count == 0:
            print("❌ FAIL: 没有调用任何工具")
            success = False
        
        if len(text_responses) == 0:
            print("❌ FAIL: 没有生成任何文本响应")
            success = False
        
        if unknown_function_found:
            print("❌ FAIL: 发现 unknown_function 错误")
            success = False
        
        if not tool_messages:
            print("❌ FAIL: 会话中没有工具消息")
            success = False
        elif not all(msg.name for msg in tool_messages):
            print("❌ FAIL: 某些工具消息缺少 name 字段")
            success = False
        
        if success:
            print("=" * 60)
            print("✅ 测试通过！所有检查都成功")
            print("=" * 60)
            return True
        else:
            print("=" * 60)
            print("❌ 测试失败！请检查上面的错误")
            print("=" * 60)
            return False


if __name__ == "__main__":
    result = asyncio.run(test_tool_followup_flow())
    sys.exit(0 if result else 1)
