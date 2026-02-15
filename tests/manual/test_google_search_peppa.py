"""
测试 Gemini 3 Google Search 功能
搜索：小猪佩奇
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


async def test_google_search_peppa_pig():
    """使用 Gemini 3 搜索小猪佩奇"""
    
    print("=" * 70)
    print("🔍 Gemini 3 Google Search 测试")
    print("=" * 70)
    print()
    print("搜索关键词: 小猪佩奇 (Peppa Pig)")
    print()
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ 未找到 GOOGLE_API_KEY 或 GEMINI_API_KEY")
        return
    
    print(f"✅ API Key 已加载 (长度: {len(api_key)})")
    print()
    
    try:
        from openclaw.agents.providers.gemini_provider import GeminiProvider
        from openclaw.agents.providers.base import LLMMessage
        
        # 使用 Gemini 3 Flash Preview
        model_name = "gemini-3-flash-preview"
        
        print(f"🤖 初始化 Provider: {model_name}")
        provider = GeminiProvider(
            model=model_name,
            api_key=api_key
        )
        print("✅ Provider 初始化成功")
        print()
        
        # 搜索小猪佩奇
        print("🔍 开始搜索...")
        print("-" * 70)
        
        messages = [
            LLMMessage(
                role="user",
                content=(
                    "请帮我搜索'小猪佩奇'的信息，包括：\n"
                    "1. 这是什么动画片\n"
                    "2. 来自哪个国家\n"
                    "3. 主要角色\n"
                    "4. 播出时间和受欢迎程度\n\n"
                    "请使用 Google 搜索获取最新的真实信息。"
                )
            )
        ]
        
        print("💬 搜索查询:")
        print(f"   {messages[0].content}")
        print()
        print("📡 正在调用 Google Search API...")
        print("-" * 70)
        print()
        
        # 启用 Google Search
        response_parts = []
        async for response in provider.stream(
            messages,
            max_tokens=1000,
            temperature=0.7,
            enable_search=True  # 🔑 启用 Google 搜索
        ):
            if response.type == "text_delta":
                text = response.content
                response_parts.append(text)
                print(text, end="", flush=True)
            elif response.type == "error":
                print(f"\n\n❌ 错误: {response.content}")
                break
            elif response.type == "done":
                break
        
        print()
        print()
        print("-" * 70)
        print("✅ 搜索完成！")
        print()
        
        # 统计信息
        full_response = "".join(response_parts)
        print("📊 结果统计:")
        print(f"   响应长度: {len(full_response)} 字符")
        print(f"   响应块数: {len(response_parts)}")
        print(f"   包含中文: {'是' if any('\u4e00' <= c <= '\u9fff' for c in full_response) else '否'}")
        print()
        
        # 验证结果
        keywords = ["小猪佩奇", "Peppa Pig", "动画", "英国", "猪"]
        found_keywords = [kw for kw in keywords if kw in full_response]
        
        print("🔑 关键词检测:")
        for keyword in keywords:
            status = "✅" if keyword in full_response else "❌"
            print(f"   {status} {keyword}")
        print()
        
        if len(found_keywords) >= 2:
            print("🎉 搜索结果验证成功！找到了相关信息。")
        else:
            print("⚠️  搜索结果可能不完整，但 API 调用成功。")
        
        print()
        print("=" * 70)
        print("✅ Google Search 测试完成！")
        print("=" * 70)
        
    except Exception as e:
        print()
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


async def test_simple_search():
    """简单搜索测试"""
    
    print("\n" + "=" * 70)
    print("🔍 简单搜索测试")
    print("=" * 70 + "\n")
    
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    try:
        from openclaw.agents.providers.gemini_provider import GeminiProvider
        from openclaw.agents.providers.base import LLMMessage
        
        provider = GeminiProvider(
            model="gemini-3-flash-preview",
            api_key=api_key
        )
        
        messages = [
            LLMMessage(
                role="user",
                content="小猪佩奇是什么？请用一段话简单介绍。"
            )
        ]
        
        print("💬 问题: 小猪佩奇是什么？")
        print("📡 使用 Google Search 获取答案...\n")
        print("-" * 70 + "\n")
        
        async for response in provider.stream(
            messages,
            max_tokens=300,
            enable_search=True
        ):
            if response.type == "text_delta":
                print(response.content, end="", flush=True)
        
        print("\n\n" + "-" * 70)
        print("✅ 简单搜索完成！\n")
        
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    print()
    print("🦞 OpenClaw Python - Google Search 功能测试")
    print()
    print("⚠️  注意:")
    print("   - 使用 Gemini 3 Flash Preview")
    print("   - 启用 Google Search 集成")
    print("   - 搜索关键词: 小猪佩奇")
    print()
    
    # 运行详细搜索测试
    asyncio.run(test_google_search_peppa_pig())
    
    # 运行简单搜索测试
    asyncio.run(test_simple_search())
    
    print()
    print("🎉 所有测试完成！")
    print()
