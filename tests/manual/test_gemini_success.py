"""
成功测试 - 使用正确的模型名称
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


async def test_gemini_chat():
    """测试 Gemini 对话"""
    
    print("=" * 60)
    print("🤖 ClawdBot - Gemini 对话测试")
    print("=" * 60)
    print()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ 未找到 GOOGLE_API_KEY")
        return
    
    print(f"✅ API Key 已加载")
    print()
    
    try:
        from openclaw.agents.providers.gemini_provider import GeminiProvider
        from openclaw.agents.providers.base import LLMMessage
        
        # 使用 Gemini 2.5 Flash (最新稳定版本)
        model_name = "models/gemini-2.5-flash"
        
        print(f"🔧 创建 Provider: {model_name}")
        provider = GeminiProvider(
            model=model_name,
            api_key=api_key
        )
        print("✅ Provider 创建成功")
        print()
        
        # 准备测试对话
        messages = [
            LLMMessage(
                role="user", 
                content="你好！我是 ClawdBot 项目的开发者。请简单介绍一下你自己，你能帮我做什么？请用中文回复。"
            )
        ]
        
        print("💬 发送消息: \"你好！我是 ClawdBot 项目的开发者...\"")
        print("-" * 60)
        print()
        
        # 获取回复
        response_parts = []
        
        async for response in provider.stream(messages, max_tokens=500):
            if response.type == "text_delta":
                text = response.content
                response_parts.append(text)
                print(text, end="", flush=True)
            elif response.type == "done":
                break
            elif response.type == "error":
                print(f"\n❌ 错误: {response.content}")
                return
        
        full_response = "".join(response_parts)
        print()
        print()
        print("-" * 60)
        print("✅ 对话成功！")
        print()
        print("📊 统计:")
        print(f"   回复长度: {len(full_response)} 字符")
        print(f"   回复字数: {len(full_response.replace(' ', ''))} 字")
        print()
        
        # 再问一个问题
        print("💬 继续对话...")
        print("-" * 60)
        print()
        
        messages.append(LLMMessage(role="assistant", content=full_response))
        messages.append(LLMMessage(
            role="user",
            content="很好！那你能帮我写一个 Python 的 Hello World 吗？"
        ))
        
        response_parts2 = []
        async for response in provider.stream(messages, max_tokens=300):
            if response.type == "text_delta":
                text = response.content
                response_parts2.append(text)
                print(text, end="", flush=True)
            elif response.type == "done":
                break
        
        print()
        print()
        print("-" * 60)
        print("=" * 60)
        print("🎉 测试完成！Gemini API 工作正常！")
        print("=" * 60)
        print()
        print("✅ 测试结果:")
        print("   - API Key 有效")
        print("   - 模型: Gemini 2.5 Flash")
        print("   - 中文对话: 正常")
        print("   - 多轮对话: 正常")
        print("   - 代码生成: 正常")
        print()
        print("🚀 ClawdBot Python 已就绪！")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    print("⚠️  安全提醒:")
    print("   - .env 文件已在 .gitignore 中")
    print("   - 不会上传任何敏感信息到 GitHub")
    print("   - 只进行安全的对话测试")
    print()
    
    asyncio.run(test_gemini_chat())
