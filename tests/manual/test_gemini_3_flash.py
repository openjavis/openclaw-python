"""
测试 Gemini 3 Flash Preview - 新 API
基于 Google 推荐的代码示例
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


async def test_gemini_3_flash():
    """测试 Gemini 3 Flash with Thinking Mode"""
    
    print("=" * 60)
    print("🚀 Gemini 3 Flash Preview 测试")
    print("=" * 60)
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
        
        # 使用 Gemini 3 Flash Preview (推荐)
        model_name = "gemini-3-flash-preview"
        
        print(f"🔧 创建 Provider: {model_name}")
        provider = GeminiProvider(
            model=model_name,
            api_key=api_key
        )
        print("✅ Provider 创建成功")
        print()
        
        # 测试 1: 基础对话
        print("📝 测试 1: 基础对话")
        print("-" * 60)
        
        messages = [
            LLMMessage(
                role="user",
                content="你好！请用一句话介绍你自己。"
            )
        ]
        
        response_parts = []
        async for response in provider.stream(messages, max_tokens=200):
            if response.type == "text_delta":
                text = response.content
                response_parts.append(text)
                print(text, end="", flush=True)
            elif response.type == "done":
                break
        
        print()
        print("✅ 测试 1 完成")
        print()
        
        # 测试 2: Thinking Mode (Gemini 3 特性)
        print("📝 测试 2: Thinking Mode (HIGH)")
        print("-" * 60)
        
        messages2 = [
            LLMMessage(
                role="user",
                content="计算 15 的平方根，然后把结果乘以 pi。请显示你的思考过程。"
            )
        ]
        
        response_parts2 = []
        async for response in provider.stream(
            messages2, 
            max_tokens=500,
            thinking_mode="HIGH"  # 启用高级思考模式
        ):
            if response.type == "text_delta":
                text = response.content
                response_parts2.append(text)
                print(text, end="", flush=True)
            elif response.type == "done":
                break
        
        print()
        print("✅ 测试 2 完成")
        print()
        
        # 测试 3: Google Search (可选)
        print("📝 测试 3: Google Search 集成")
        print("-" * 60)
        
        messages3 = [
            LLMMessage(
                role="user",
                content="OpenClaw 是什么项目？请搜索最新信息。"
            )
        ]
        
        response_parts3 = []
        async for response in provider.stream(
            messages3,
            max_tokens=300,
            enable_search=True  # 启用 Google 搜索
        ):
            if response.type == "text_delta":
                text = response.content
                response_parts3.append(text)
                print(text, end="", flush=True)
            elif response.type == "done":
                break
        
        print()
        print("✅ 测试 3 完成")
        print()
        
        # 总结
        print("=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)
        print()
        print("✅ 测试结果:")
        print(f"   模型: {model_name}")
        print(f"   基础对话: {len(response_parts)} 块")
        print(f"   Thinking Mode: {len(response_parts2)} 块")
        print(f"   Google Search: {len(response_parts3)} 块")
        print()
        print("🚀 Gemini 3 Flash Preview 工作正常！")
        print()
        print("💡 推荐配置:")
        print("   model: gemini-3-flash-preview")
        print("   thinking_mode: HIGH (for complex tasks)")
        print("   enable_search: True (for real-time info)")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


async def list_available_models():
    """列出可用的 Gemini 模型"""
    print("\n" + "=" * 60)
    print("📋 可用的 Gemini 模型")
    print("=" * 60 + "\n")
    
    from openclaw.agents.providers.gemini_provider import GEMINI_MODELS
    
    recommended = []
    stable = []
    others = []
    
    for model_id, info in GEMINI_MODELS.items():
        if "alias" in info:
            continue  # Skip alias entries
        
        if info.get("recommended"):
            recommended.append((model_id, info))
        elif info.get("stable"):
            stable.append((model_id, info))
        else:
            others.append((model_id, info))
    
    print("🌟 推荐模型 (Recommended):")
    for model_id, info in recommended:
        features = ", ".join(info.get("features", []))
        print(f"  • {model_id}")
        print(f"    {info['name']}")
        print(f"    Context: {info['context_window']:,} tokens")
        print(f"    Features: {features}")
        print()
    
    print("✨ 稳定版本 (Stable):")
    for model_id, info in stable:
        features = ", ".join(info.get("features", []))
        print(f"  • {model_id}")
        print(f"    {info['name']}")
        print(f"    Context: {info['context_window']:,} tokens")
        print()
    
    print("📦 其他模型:")
    for model_id, info in others:
        print(f"  • {model_id} - {info['name']}")


if __name__ == "__main__":
    print()
    print("⚠️  安全提醒:")
    print("   - .env 文件已在 .gitignore 中")
    print("   - 不会上传任何敏感信息")
    print()
    
    # 列出可用模型
    asyncio.run(list_available_models())
    
    # 运行测试
    asyncio.run(test_gemini_3_flash())
