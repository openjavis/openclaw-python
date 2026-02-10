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
        from openclaw.agents.system_prompt_bootstrap import load_bootstrap_files, format_bootstrap_context
        from openclaw.agents.system_prompt_params import build_system_prompt_params, get_runtime_info
        
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
            enable_search=False,  # 禁用 Gemini 内置搜索，使用我们的工具
            thinking_mode="HIGH"  # gemini-3-pro-preview 需要 thinking mode 才能正常工作
        )
        logger.info("✅ Agent Runtime 创建成功 (thinking_mode=HIGH)")
        
        # 4. 创建 Session Manager
        logger.info("📁 创建 Session Manager...")
        workspace_dir = Path.home() / ".openclaw" / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        session_manager = SessionManager(workspace_dir=workspace_dir)
        logger.info(f"✅ Session Manager 创建成功: {workspace_dir}")
        
        # 5. 创建 Tool Registry 并注册工具
        logger.info("🔧 创建 Tool Registry...")
        
        # Create tool registry without auto-register, we'll register manually
        tool_registry = ToolRegistry(
            session_manager=session_manager,
            auto_register=False  # Manual registration to inject config
        )
        
        # Get exec config from settings
        exec_config = {
            "security": config.tools.exec.security,
            "safe_bins": config.tools.exec.safe_bins,
            "path_prepend": config.tools.exec.path_prepend,
            "timeout_sec": config.tools.exec.timeout_sec,
            "host": config.tools.exec.host,
        }
        logger.info(f"   Exec config: security={exec_config['security']}, timeout={exec_config['timeout_sec']}s")
        
        # Manually register tools with config
        from openclaw.agents.tools.bash import BashTool
        from openclaw.agents.tools.file_ops import ReadFileTool, WriteFileTool, EditFileTool
        from openclaw.agents.tools.web import WebFetchTool, WebSearchTool
        from openclaw.agents.tools.image import ImageTool
        from openclaw.agents.tools.browser import BrowserTool
        from openclaw.agents.tools.cron import CronTool
        from openclaw.agents.tools.tts import TTSTool
        from openclaw.agents.tools.process import ProcessTool
        from openclaw.agents.tools.apply_patch import ApplyPatchTool
        
        # Register bash tool with exec config
        tool_registry.register(BashTool(exec_config=exec_config, workspace_dir=workspace_dir))
        
        # Register file operations
        tool_registry.register(ReadFileTool())
        tool_registry.register(WriteFileTool())
        tool_registry.register(EditFileTool())
        
        # Register web tools
        tool_registry.register(WebFetchTool())
        tool_registry.register(WebSearchTool())
        
        # Register image tool with model_has_vision=True for Gemini 3 Pro
        tool_registry.register(ImageTool(
            workspace_root=workspace_dir,
            model_has_vision=True,  # Gemini 3 Pro has vision
            optimize_images=True
        ))
        
        # Register advanced tools
        tool_registry.register(BrowserTool())
        tool_registry.register(CronTool())
        tool_registry.register(TTSTool())
        tool_registry.register(ProcessTool())
        tool_registry.register(ApplyPatchTool())
        
        # Note: Session management tools and channel tools are added by ToolRegistry
        # when session_manager and channel_registry are available
        
        tools = tool_registry.list_tools()
        tool_names = [tool.name for tool in tools]
        logger.info(f"✅ Tool Registry 创建成功，注册了 {len(tools)} 个工具")
        logger.info(f"   工具列表: {tool_names[:5]}{'...' if len(tools) > 5 else ''}")
        logger.info(f"   Bash tool: security={exec_config['security']}, safe_bins count={len(exec_config['safe_bins'])}")
        
        # 6. 加载 Skills
        logger.info("📚 加载 Skills...")
        try:
            skill_loader = SkillLoader()
            
            # 从多个目录加载 skills
            # Add project's own skills directory first
            project_skills_dir = Path(__file__).parent / "openclaw" / "skills"
            bundled_skills_dir = Path.home() / ".openclaw" / "bundled-skills"
            managed_skills_dir = Path.home() / ".openclaw" / "skills"
            workspace_skills_dir = workspace_dir / "skills"
            
            # 创建目录（如果不存在）
            managed_skills_dir.mkdir(parents=True, exist_ok=True)
            workspace_skills_dir.mkdir(parents=True, exist_ok=True)
            
            all_skills = []
            skill_sources = [
                (project_skills_dir, "project-bundled"),  # NEW: Project's own skills
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
        
        # 7. 构建 System Prompt (使用新架构)
        logger.info("📝 构建 System Prompt...")
        
        # Build runtime params
        params = build_system_prompt_params(
            config=config,
            workspace_dir=workspace_dir,
            runtime={
                "agent_id": "main",
                "model": model,
                "channel": "telegram"
            }
        )
        
        # Load bootstrap files
        bootstrap_files = load_bootstrap_files(workspace_dir)
        context_files = format_bootstrap_context(bootstrap_files)
        
        # Build system prompt with new parameters
        system_prompt = build_agent_system_prompt(
            workspace_dir=workspace_dir,
            tool_names=tool_names,
            tool_summaries=None,  # uses CORE_TOOL_SUMMARIES defaults
            skills_prompt=skills_prompt,
            prompt_mode="full",
            runtime_info=params["runtime_info"],
            exec_config=exec_config,  # Pass exec config to inform agent
            user_timezone=params["user_timezone"],
            context_files=context_files,
        )
        
        logger.info(f"✅ System Prompt 构建成功 ({len(system_prompt)} 字符)")
        if params["user_timezone"]:
            logger.info(f"   时区: {params['user_timezone']}")
        if params["repo_root"]:
            logger.info(f"   Git 仓库: {params['repo_root']}")
        if eligible_skills:
            logger.info(f"   包含 {len(eligible_skills)} 个 skills")
        logger.info(f"   加载了 {len(context_files)} 个 bootstrap 文件")
        
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
