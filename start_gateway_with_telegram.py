#!/usr/bin/env python3
"""
启动 OpenClaw Gateway 并启用 Telegram channel
"""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """主启动函数"""
    try:
        # 导入所需模块
        from openclaw.config import load_config
        from openclaw.gateway.server import GatewayServer
        from openclaw.channels.telegram import TelegramChannel
        from openclaw.agents.runtime import MultiProviderRuntime
        from openclaw.agents.session import SessionManager
        from openclaw.agents.tools.registry import ToolRegistry
        from openclaw.skills.loader import SkillLoader
        from openclaw.agents.system_prompt import build_agent_system_prompt, format_skills_for_prompt
        
        logger.info("=" * 60)
        logger.info("🚀 启动 OpenClaw Gateway with Telegram")
        logger.info("=" * 60)
        
        # 1. 加载配置
        logger.info("📋 加载配置...")
        config = load_config()
        
        # 2. 获取 Telegram Bot Token
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN 未配置")
            return
        
        logger.info(f"✅ Telegram Bot Token: {bot_token[:10]}...")
        
        # 3. 创建 Agent Runtime (自动检测 Provider)
        logger.info("🤖 创建 Agent Runtime...")
        
        # 从配置中获取模型，或使用自动检测
        model = None
        
        if hasattr(config.agent, 'model') and config.agent.model:
            model = config.agent.model
            logger.info(f"   使用配置的模型: {model}")
        elif os.getenv("GOOGLE_API_KEY"):
            model = "google/gemini-3-flash-preview"
            logger.info(f"   自动检测到 GOOGLE_API_KEY，使用: {model}")
        elif os.getenv("ANTHROPIC_API_KEY"):
            model = "anthropic/claude-3-5-sonnet-20241022"
            logger.info(f"   自动检测到 ANTHROPIC_API_KEY，使用: {model}")
        elif os.getenv("OPENAI_API_KEY"):
            model = "openai/gpt-4"
            logger.info(f"   自动检测到 OPENAI_API_KEY，使用: {model}")
        else:
            logger.error("❌ 没有配置任何 API Key")
            return
        
        # 不启用 Gemini 内置 Google Search，使用我们注册的 web_search 工具
        # 原始 OpenClaw 使用 Brave Search 作为 web_search 工具
        # 我们使用 DuckDuckGo 实现的 web_search (在 19 个工具中)
        logger.info(f"   📋 将使用注册的 19 个工具（包括 web_search）")
        
        runtime = MultiProviderRuntime(
            model=model,
            enable_search=False  # 禁用 Gemini 内置搜索，使用我们的工具
        )
        logger.info("✅ Agent Runtime 创建成功")
        
        # 4. 创建 Session Manager
        logger.info("📁 创建 Session Manager...")
        workspace_dir = Path.home() / ".openclaw" / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        session_manager = SessionManager(workspace_dir=workspace_dir)
        logger.info(f"✅ Session Manager 创建成功: {workspace_dir}")
        
        # 5. 创建 Tool Registry 并注册工具
        logger.info("🔧 创建 Tool Registry...")
        tool_registry = ToolRegistry(
            session_manager=session_manager,
            auto_register=True  # 自动注册默认工具
        )
        tools = tool_registry.list_tools()
        tool_names = [tool.name for tool in tools]
        logger.info(f"✅ Tool Registry 创建成功，注册了 {len(tools)} 个工具")
        logger.info(f"   工具列表: {tool_names[:5]}{'...' if len(tools) > 5 else ''}")
        
        # 6. 加载 Skills
        logger.info("📚 加载 Skills...")
        try:
            skill_loader = SkillLoader()
            
            # 从多个目录加载 skills
            bundled_skills_dir = Path.home() / ".openclaw" / "bundled-skills"
            managed_skills_dir = Path.home() / ".openclaw" / "skills"
            workspace_skills_dir = workspace_dir / "skills"
            
            # 创建目录（如果不存在）
            managed_skills_dir.mkdir(parents=True, exist_ok=True)
            workspace_skills_dir.mkdir(parents=True, exist_ok=True)
            
            all_skills = []
            skill_sources = [
                (bundled_skills_dir, "bundled"),
                (managed_skills_dir, "managed"),
                (workspace_skills_dir, "workspace")
            ]
            
            for skills_dir, source in skill_sources:
                if skills_dir.exists():
                    loaded = skill_loader.load_from_directory(skills_dir, source=source)
                    all_skills.extend(loaded)
                    logger.debug(f"   从 {skills_dir} ({source}) 加载了 {len(loaded)} 个 skills")
            
            # 过滤合格的 skills
            eligible_skills_dict = skill_loader.get_eligible_skills()
            eligible_skills = list(eligible_skills_dict.values())
            logger.info(f"✅ Skills 加载成功，{len(all_skills)} 个总计，{len(eligible_skills)} 个合格")
            
            # 格式化 skills 为提示
            skills_for_prompt = [
                {
                    "name": skill.name,
                    "description": skill.metadata.description or "No description",
                    "location": str(Path(skill.content).parent / "SKILL.md") if hasattr(skill, 'file_path') else "",
                    "tags": skill.metadata.tags or []
                }
                for skill in eligible_skills
            ]
            skills_prompt = format_skills_for_prompt(skills_for_prompt)
            
        except Exception as e:
            logger.warning(f"⚠️  Skills 加载失败: {e}")
            skills_prompt = None
            eligible_skills = []
        
        # 7. 构建 System Prompt (添加当前日期信息)
        logger.info("📝 构建 System Prompt...")
        from datetime import datetime
        current_date = datetime.now().strftime("%Y年%m月%d日")
        
        system_prompt = build_agent_system_prompt(
            workspace_dir=workspace_dir,
            tool_names=tool_names,
            skills_prompt=skills_prompt,
            mode="full"
        )
        # 在 system prompt 中添加当前日期
        system_prompt = f"{system_prompt}\n\n## Current Date\nToday is: {current_date}\n"
        
        logger.info(f"✅ System Prompt 构建成功 ({len(system_prompt)} 字符)")
        logger.info(f"   当前日期: {current_date}")
        if eligible_skills:
            logger.info(f"   包含 {len(eligible_skills)} 个 skills")
        
        # 8. 创建 Gateway Server (传递工具和 system prompt)
        logger.info("🌐 创建 Gateway Server...")
        gateway = GatewayServer(
            config=config,
            agent_runtime=runtime,
            session_manager=session_manager,
            tools=tools,  # 传递工具列表
            system_prompt=system_prompt,  # 传递 system prompt
            auto_discover_channels=False  # 手动注册
        )
        logger.info("✅ Gateway Server 创建成功")
        
        # 9. 注册并配置 Telegram Channel
        logger.info("📱 注册 Telegram Channel...")
        gateway.channel_manager.register("telegram", TelegramChannel)
        
        telegram_config = {
            "enabled": True,
            "botToken": bot_token,
            "dmPolicy": "open",  # 允许所有人发送消息
        }
        gateway.channel_manager.configure("telegram", telegram_config)
        logger.info("✅ Telegram Channel 已注册并配置")
        
        # 10. 启动 Gateway (会自动启动所有 enabled 的 channels)
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"🎉 Gateway 启动在 ws://127.0.0.1:{config.gateway.port}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📋 配置信息:")
        logger.info(f"  - 模型: {model}")
        logger.info(f"  - 工具数量: {len(tools)}")
        logger.info(f"  - Skills 数量: {len(eligible_skills)}")
        logger.info(f"  - System Prompt: {len(system_prompt)} 字符")
        logger.info(f"  - Telegram Bot: @whatisnewzhaobot")
        logger.info(f"  - DM Policy: open (允许所有人)")
        logger.info(f"  - Workspace: {workspace_dir}")
        logger.info("")
        logger.info("💬 在 Telegram 中发送消息给 @whatisnewzhaobot 开始对话")
        logger.info("")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 60)
        logger.info("")
        
        # 启动 Gateway
        await gateway.start(start_channels=True)
        
    except KeyboardInterrupt:
        logger.info("\n\n🛑 Gateway 停止")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
