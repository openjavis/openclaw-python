#!/usr/bin/env python3
"""
Start OpenClaw Gateway and enable Telegram channel
"""
import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    """Main startup function"""
    try:
        # Import required modules
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
        logger.info("🚀 Starting OpenClaw Gateway with Telegram")
        logger.info("=" * 60)
        
        # 1. Load configuration
        logger.info("📋 Loading configuration...")
        config = load_config()
        
        # 2. Get Telegram Bot Token
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not configured")
            return
        
        logger.info(f"✅ Telegram Bot Token: {bot_token[:10]}...")
        
        # 3. Create Agent Runtime (auto-detect Provider)
        logger.info("🤖 Creating Agent Runtime...")
        
        # Get model from config or use auto-detection
        model = None
        
        if hasattr(config.agent, 'model') and config.agent.model:
            model = config.agent.model
            logger.info(f"   Using configured model: {model}")
        elif os.getenv("GOOGLE_API_KEY"):
            model = "google/gemini-3-flash-preview"
            logger.info(f"   Auto-detected GOOGLE_API_KEY, using: {model}")
        elif os.getenv("ANTHROPIC_API_KEY"):
            model = "anthropic/claude-3-5-sonnet-20241022"
            logger.info(f"   Auto-detected ANTHROPIC_API_KEY, using: {model}")
        elif os.getenv("OPENAI_API_KEY"):
            model = "openai/gpt-4"
            logger.info(f"   Auto-detected OPENAI_API_KEY, using: {model}")
        else:
            logger.error("❌ No API Key configured")
            return
        
        # Disable Gemini's built-in Google Search, use our registered web_search tool
        # Original OpenClaw uses Brave Search as web_search tool
        # We use DuckDuckGo implementation of web_search (in 19 tools)
        logger.info(f"   📋 Will use registered 19 tools (including web_search)")
        
        runtime = MultiProviderRuntime(
            model=model,
            enable_search=False,  # Disable Gemini's built-in search, use our tools
            thinking_mode="HIGH"  # gemini-3-pro-preview requires thinking mode to work properly
        )
        logger.info("✅ Agent Runtime created successfully (thinking_mode=HIGH)")
        
        # 4. Create Session Manager
        logger.info("📁 Creating Session Manager...")
        workspace_dir = Path.home() / ".openclaw" / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        session_manager = SessionManager(workspace_dir=workspace_dir)
        logger.info(f"✅ Session Manager created successfully: {workspace_dir}")
        
        # 5. Create Tool Registry and register tools
        logger.info("🔧 Creating Tool Registry...")
        
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
        logger.info(f"✅ Tool Registry created successfully, registered {len(tools)} tools")
        logger.info(f"   Tool list: {tool_names[:5]}{'...' if len(tools) > 5 else ''}")
        logger.info(f"   Bash tool: security={exec_config['security']}, safe_bins count={len(exec_config['safe_bins'])}")
        
        # 6. Load Skills
        logger.info("📚 Loading Skills...")
        try:
            skill_loader = SkillLoader()
            
            # Load skills from multiple directories
            # Add project's own skills directory first
            project_skills_dir = Path(__file__).parent / "openclaw" / "skills"
            bundled_skills_dir = Path.home() / ".openclaw" / "bundled-skills"
            managed_skills_dir = Path.home() / ".openclaw" / "skills"
            workspace_skills_dir = workspace_dir / "skills"
            
            # Create directories if they don't exist
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
                    logger.debug(f"   Loaded {len(loaded)} skills from {skills_dir} ({source})")
            
            # Filter eligible skills
            eligible_skills_dict = skill_loader.get_eligible_skills()
            eligible_skills = list(eligible_skills_dict.values())
            logger.info(f"✅ Skills loaded successfully, {len(all_skills)} total, {len(eligible_skills)} eligible")
            
            # Format skills for prompt
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
            logger.warning(f"⚠️  Failed to load skills: {e}")
            skills_prompt = None
            eligible_skills = []
        
        # 7. Build System Prompt (using new architecture)
        logger.info("📝 Building System Prompt...")
        
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
        
        logger.info(f"✅ System Prompt built successfully ({len(system_prompt)} characters)")
        if params["user_timezone"]:
            logger.info(f"   Timezone: {params['user_timezone']}")
        if params["repo_root"]:
            logger.info(f"   Git repository: {params['repo_root']}")
        if eligible_skills:
            logger.info(f"   Includes {len(eligible_skills)} skills")
        logger.info(f"   Loaded {len(context_files)} bootstrap files")
        
        # 8. Create Gateway Server (passing tools and system prompt)
        logger.info("🌐 Creating Gateway Server...")
        gateway = GatewayServer(
            config=config,
            agent_runtime=runtime,
            session_manager=session_manager,
            tools=tools,  # Pass tool list
            system_prompt=system_prompt,  # Pass system prompt
            auto_discover_channels=False  # Manual registration
        )
        logger.info("✅ Gateway Server created successfully")
        
        # 9. Register and configure Telegram Channel
        logger.info("📱 Registering Telegram Channel...")
        gateway.channel_manager.register("telegram", TelegramChannel)
        
        telegram_config = {
            "enabled": True,
            "botToken": bot_token,
            "dmPolicy": "open",  # Allow all to send messages
        }
        gateway.channel_manager.configure("telegram", telegram_config)
        logger.info("✅ Telegram Channel registered and configured")
        
        # 10. Start Gateway (will automatically start all enabled channels)
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"🎉 Gateway started at ws://127.0.0.1:{config.gateway.port}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📋 Configuration:")
        logger.info(f"  - Model: {model}")
        logger.info(f"  - Tools count: {len(tools)}")
        logger.info(f"  - Skills count: {len(eligible_skills)}")
        logger.info(f"  - System Prompt: {len(system_prompt)} characters")
        logger.info(f"  - Telegram Bot: @whatisnewzhaobot")
        logger.info(f"  - DM Policy: open (allow all)")
        logger.info(f"  - Workspace: {workspace_dir}")
        logger.info("")
        logger.info("💬 Send a message to @whatisnewzhaobot in Telegram to start conversation")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        logger.info("")
        
        # Start Gateway
        await gateway.start(start_channels=True)
        
    except KeyboardInterrupt:
        logger.info("\n\n🛑 Gateway stopped")
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
