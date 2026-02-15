#!/usr/bin/env python3
"""测试工具消息的 name 字段是否正确保存和读取"""

from openclaw.agents.session import Session, Message
from pathlib import Path
import tempfile
import json


def test_tool_message_name_preservation():
    """测试工具消息的 name 字段是否正确保存"""
    # 创建临时会话
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        session = Session(
            session_id="test-tool-name",
            workspace_dir=workspace,
            session_key="test-tool-name"
        )
        
        print("=" * 60)
        print("测试 1: 添加工具消息")
        print("=" * 60)
        
        # 添加工具消息
        tool_msg = session.add_tool_message(
            tool_call_id="call_abc123",
            content="Tool execution result",
            name="bash"
        )
        
        print(f"✅ 添加的消息:")
        print(f"  - role: {tool_msg.role}")
        print(f"  - content: {tool_msg.content}")
        print(f"  - tool_call_id: {tool_msg.tool_call_id}")
        print(f"  - name: {tool_msg.name}")
        print()
        
        assert tool_msg.name == "bash", f"Expected name='bash', got '{tool_msg.name}'"
        
        print("=" * 60)
        print("测试 2: 从 Session 读取消息")
        print("=" * 60)
        
        messages = session.get_messages()
        assert len(messages) > 0, "No messages found"
        
        msg = messages[-1]
        print(f"✅ 读取的消息:")
        print(f"  - role: {msg.role}")
        print(f"  - content: {msg.content}")
        print(f"  - tool_call_id: {msg.tool_call_id}")
        print(f"  - name: {msg.name}")
        print()
        
        if msg.name == "bash":
            print("✅ PASS: name 字段正确保存到内存")
        else:
            print(f"❌ FAIL: name 字段丢失或错误，expected 'bash', got '{msg.name}'")
            assert False, f"Name field lost in memory, expected 'bash', got '{msg.name}'"
        print()
        
        print("=" * 60)
        print("测试 3: 保存到磁盘并重新读取")
        print("=" * 60)
        
        # 保存到磁盘
        session._save()
        session_file = session._session_file
        print(f"✅ 保存到: {session_file}")
        
        # 读取文件内容
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
                print(f"✅ 文件内容:")
                print(f"  - messages count: {len(data.get('messages', []))}")
                if data.get('messages'):
                    last_msg = data['messages'][-1]
                    print(f"  - 最后一条消息:")
                    print(f"    - role: {last_msg.get('role')}")
                    print(f"    - name: {last_msg.get('name')}")
                    print(f"    - tool_call_id: {last_msg.get('tool_call_id')}")
                    
                    if last_msg.get('name') == 'bash':
                        print("✅ PASS: name 字段正确保存到磁盘")
                    else:
                        print(f"❌ FAIL: name 字段在磁盘上丢失，expected 'bash', got '{last_msg.get('name')}'")
                        assert False, f"Name field lost on disk, expected 'bash', got '{last_msg.get('name')}'"
        else:
            print(f"❌ FAIL: 会话文件不存在")
            assert False, "Session file does not exist"
        
        print()
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)


if __name__ == "__main__":
    test_tool_message_name_preservation()
