"""测试 follow-up call 时消息转换是否保留 name 字段"""

from openclaw.agents.session import Session, Message
from openclaw.agents.history_utils import sanitize_session_history, limit_history_turns
from pathlib import Path
import tempfile


def test_followup_message_conversion():
    """测试消息转换流程"""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        session = Session(
            session_id="test-followup",
            workspace_dir=workspace,
            session_key="test-followup"
        )
        
        print("=" * 60)
        print("步骤 1: 模拟初始对话")
        print("=" * 60)
        
        # 添加用户消息
        session.add_user_message("今天是哪一天？")
        
        # 添加助手工具调用
        session.add_assistant_message(
            content="",
            tool_calls=[{
                "id": "call_123",
                "name": "bash",
                "arguments": {"command": "date"}
            }]
        )
        
        # 添加工具结果
        tool_msg = session.add_tool_message(
            tool_call_id="call_123",
            content="2024-02-16",
            name="bash"  # ⚠️ 关键：这里有 name
        )
        
        print(f"✅ 添加工具消息: name={tool_msg.name}")
        print()
        
        print("=" * 60)
        print("步骤 2: 读取消息（模拟 follow-up call）")
        print("=" * 60)
        
        # 获取所有消息
        followup_all_messages = session.get_messages()
        print(f"✅ 读取 {len(followup_all_messages)} 条消息")
        
        # 检查工具消息
        for i, msg in enumerate(followup_all_messages):
            print(f"  消息 {i}: role={msg.role}, name={msg.name}, tool_call_id={msg.tool_call_id}")
        print()
        
        print("=" * 60)
        print("步骤 3: 转换为字典（模拟 runtime.py Line 1057-1066）")
        print("=" * 60)
        
        # 模拟 runtime.py 的转换逻辑
        followup_messages_dict = [
            {
                "role": m.role,
                "content": m.content,
                "tool_calls": getattr(m, 'tool_calls', None),
                "tool_call_id": getattr(m, 'tool_call_id', None),
                "name": getattr(m, 'name', None),  # ⚠️ 关键：这里应该读取 name
            }
            for m in followup_all_messages
        ]
        
        # 检查转换后的字典
        for i, msg_dict in enumerate(followup_messages_dict):
            if msg_dict['role'] == 'tool':
                print(f"  工具消息 {i}:")
                print(f"    - name: {msg_dict.get('name')}")
                print(f"    - tool_call_id: {msg_dict.get('tool_call_id')}")
                
                if msg_dict.get('name') == 'bash':
                    print("    ✅ PASS: name 字段保留")
                else:
                    print(f"    ❌ FAIL: name 字段丢失，got '{msg_dict.get('name')}'")
        print()
        
        print("=" * 60)
        print("步骤 4: 经过 sanitize 和 limit")
        print("=" * 60)
        
        followup_sanitized = sanitize_session_history(followup_messages_dict)
        followup_limited = limit_history_turns(
            followup_sanitized,
            max_turns=10,
            provider="gemini"
        )
        
        print(f"✅ Sanitized: {len(followup_sanitized)} 条消息")
        print(f"✅ Limited: {len(followup_limited)} 条消息")
        
        # 检查最终消息
        for i, msg_dict in enumerate(followup_limited):
            if msg_dict['role'] == 'tool':
                print(f"  工具消息 {i}:")
                print(f"    - name: {msg_dict.get('name')}")
                print(f"    - tool_call_id: {msg_dict.get('tool_call_id')}")
                
                if msg_dict.get('name') == 'bash':
                    print("    ✅ PASS: name 字段经过处理后仍保留")
                else:
                    print(f"    ❌ FAIL: name 字段在处理后丢失，got '{msg_dict.get('name')}'")
        print()
        
        print("=" * 60)
        print("测试完成")
        print("=" * 60)


if __name__ == "__main__":
    test_followup_message_conversion()
