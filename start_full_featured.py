#!/usr/bin/env python3
"""
OpenClaw Python - 完整功能启动脚本

包含功能：
✅ Gateway Server + WebSocket API
✅ 所有内置 Tools (24+ 工具)
✅ 所有 Skills (50+ 技能)
✅ 完整 Memory 管理（自动压缩、持久化）
✅ Context Management（智能上下文管理）
✅ 多频道支持 (Telegram/Discord/Slack)
✅ Event Broadcasting（实时事件广播）
✅ Session Management（会话管理）
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import SessionManager
from openclaw.agents.tools.registry import ToolRegistry
from openclaw.skills.loader import get_skill_loader
from openclaw.channels.enhanced_telegram import EnhancedTelegramChannel
from openclaw.config import ClawdbotConfig
from openclaw.gateway import GatewayServer
from openclaw.monitoring import setup_logging

logger = logging.getLogger(__name__)


class FullFeaturedServer:
    """
    完整功能的 OpenClaw 服务器
    
    功能：
    - ✅ 所有工具 (Browser, Bash, File, Web, Image, TTS, Cron, etc.)
    - ✅ 所有技能 (50+ skills)
    - ✅ 完整 Memory 管理
    - ✅ Context 自动压缩
    - ✅ Gateway + WebSocket
    - ✅ 多频道支持
    """
    
    def __init__(self, config: ClawdbotConfig):
        self.config = config
        self.running = False
        
        # =================================================================
        # 1. Workspace 和 Session 管理
        # =================================================================
        workspace = Path("./workspace")
        workspace.mkdir(exist_ok=True)
        
        self.session_manager = SessionManager(workspace)
        logger.info(f"✅ Session Manager initialized: {workspace}")
        
        # =================================================================
        # 2. 加载所有 Tools
        # =================================================================
        self.tool_registry = ToolRegistry(
            session_manager=self.session_manager,
            channel_registry=None,  # 稍后设置
            auto_register=True  # 自动注册所有默认工具
        )
        
        self.all_tools = self.tool_registry.list_tools()
        logger.info(f"✅ Loaded {len(self.all_tools)} tools: {[t.name for t in self.all_tools]}")
        
        # =================================================================
        # 3. 加载所有 Skills
        # =================================================================
        skill_loader = get_skill_loader()
        all_skills = skill_loader.load_all_skills()
        eligible_skills = skill_loader.get_eligible_skills()
        
        logger.info(f"✅ Loaded {len(all_skills)} skills ({len(eligible_skills)} eligible)")
        logger.info(f"   Skills: {list(eligible_skills.keys())[:10]}... (showing first 10)")
        
        # 将 skills 转换为系统提示
        self.skills_prompt = self._build_skills_prompt(eligible_skills)
        
        # =================================================================
        # 4. Agent Runtime（启用所有高级功能）
        # =================================================================
        model = getattr(config.agent, "model", "gemini/gemini-3-flash-preview")
        
        self.agent_runtime = AgentRuntime(
            model=model,
            enable_context_management=True,  # ✅ 启用上下文管理
            max_retries=3,
            # 高级功能
            thinking_mode="OFF",  # 可选: OFF/LOW/MEDIUM/HIGH
            fallback_models=[],   # 备用模型
            enable_queuing=False,  # 队列管理
            tool_format="MARKDOWN",  # 工具格式
            compaction_strategy="KEEP_IMPORTANT",  # 压缩策略
        )
        
        logger.info("✅ Agent Runtime initialized with advanced features")
        logger.info(f"   - Model: {model}")
        logger.info("   - Context Management: ✅ Enabled")
        logger.info("   - Auto Compaction: ✅ Enabled")
        logger.info("   - Memory Persistence: ✅ Enabled")
        
        # =================================================================
        # 5. Gateway Server（包含 WebSocket API）
        # =================================================================
        self.gateway = GatewayServer(
            config=config,
            agent_runtime=self.agent_runtime,
            session_manager=self.session_manager,
            tools=self.all_tools,
            system_prompt=self.skills_prompt,  # ✨ 传递 Skills Prompt
            auto_discover_channels=False,
        )
        
        self.channel_manager = self.gateway.channel_manager
        logger.info("✅ Gateway Server initialized")
        logger.info(f"✨ Skills prompt loaded ({len(self.skills_prompt)} chars)")
        
    def _build_skills_prompt(self, skills: dict) -> str:
        """构建 skills 系统提示"""
        if not skills:
            return ""
        
        prompt = "\n\n# Your Capabilities and Skills\n\n"
        prompt += "You are an advanced AI assistant with the following capabilities:\n\n"
        
        # 添加工具说明
        prompt += "## Available Tools\n"
        prompt += "You have access to these powerful tools:\n"
        prompt += "- **bash**: Execute shell commands (ls, cat, grep, etc.)\n"
        prompt += "- **read_file, write_file, edit_file**: File operations\n"
        prompt += "- **web_fetch, web_search**: Web access and search\n"
        prompt += "- **browser**: Browser automation (open pages, screenshots)\n"
        prompt += "- **image**: Image generation and analysis\n"
        prompt += "- **cron**: Schedule tasks\n"
        prompt += "- **tts**: Text-to-speech\n"
        prompt += "- And 12 more tools for various tasks\n\n"
        
        # 添加 Skills 说明
        prompt += "## Specialized Skills\n"
        prompt += f"You have {len(skills)} specialized skills for different tasks:\n\n"
        
        # 重点展示前10个 skills
        for name, skill in list(skills.items())[:10]:
            desc = skill.metadata.description or 'No description'
            prompt += f"- **{name}**: {desc}\n"
        
        if len(skills) > 10:
            remaining = list(skills.items())[10:20]
            prompt += f"\nAdditional skills: {', '.join([s[0] for s in remaining])}"
            if len(skills) > 20:
                prompt += f", and {len(skills) - 20} more.\n"
            else:
                prompt += "\n"
        
        prompt += "\n## How to Use\n"
        prompt += "- When asked to do something, think about which tools and skills can help\n"
        prompt += "- You can execute bash commands to check system info, run scripts, etc.\n"
        prompt += "- You can read/write files, search the web, generate images, and more\n"
        prompt += "- Use your skills to provide expert assistance in various domains\n"
        
        return prompt
    
    def setup_channels(self) -> None:
        """注册和配置频道"""
        # Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            self.channel_manager.register(
                channel_id="telegram",
                channel_class=EnhancedTelegramChannel,
                config={
                    "bot_token": bot_token,
                    "parse_mode": "Markdown",
                },
            )
            logger.info("✅ Telegram channel registered")
        else:
            logger.warning("⚠️  TELEGRAM_BOT_TOKEN not set")
        
        # Discord（如果配置）
        discord_token = os.getenv("DISCORD_BOT_TOKEN")
        if discord_token:
            try:
                from openclaw.channels.enhanced_discord import EnhancedDiscordChannel
                self.channel_manager.register(
                    channel_id="discord",
                    channel_class=EnhancedDiscordChannel,
                    config={"bot_token": discord_token},
                )
                logger.info("✅ Discord channel registered")
            except ImportError:
                logger.warning("⚠️  Discord channel not available")
        
        # Slack（如果配置）
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if slack_token:
            try:
                from openclaw.channels.enhanced_slack import EnhancedSlackChannel
                self.channel_manager.register(
                    channel_id="slack",
                    channel_class=EnhancedSlackChannel,
                    config={"bot_token": slack_token},
                )
                logger.info("✅ Slack channel registered")
            except ImportError:
                logger.warning("⚠️  Slack channel not available")
        
        channels = self.channel_manager.list_channels()
        logger.info(f"✅ Registered {len(channels)} channels")
    
    async def start(self) -> None:
        """启动完整功能服务器"""
        logger.info("🚀 Starting Full-Featured OpenClaw Server...")
        
        # 设置频道
        self.setup_channels()
        
        self.running = True
        
        # 打印启动信息
        print()
        print("=" * 70)
        print("🦞 OpenClaw Python - 完整功能服务器")
        print("=" * 70)
        print()
        print("✅ 已启用功能:")
        print()
        print("  📦 Tools:")
        print(f"     • {len(self.all_tools)} 个工具已加载")
        print(f"     • {', '.join([t.name for t in self.all_tools[:8]])}...")
        print()
        print("  🎯 Skills:")
        skill_loader = get_skill_loader()
        eligible = skill_loader.get_eligible_skills()
        print(f"     • {len(eligible)} 个技能可用")
        print(f"     • {', '.join(list(eligible.keys())[:6])}...")
        print()
        print("  🧠 Memory & Context:")
        print("     • Session persistence: ✅ Enabled")
        print("     • Auto context compression: ✅ Enabled")
        print("     • Message history: ✅ Unlimited (auto-compressed)")
        print("     • Strategy: KEEP_IMPORTANT")
        print()
        print("  🌐 Network:")
        channels = self.channel_manager.list_channels()
        print(f"     • Channels: {', '.join(channels) if channels else 'None'}")
        print("     • WebSocket API: ws://localhost:8765")
        print("     • Event Broadcasting: ✅ Enabled")
        print()
        print("  🤖 AI Model:")
        model_name = getattr(self.config.agent, "model", "gemini/gemini-3-flash-preview")
        print(f"     • Model: {model_name}")
        print(f"     • Provider: Gemini")
        print()
        print("=" * 70)
        print()
        print("💡 提示:")
        print("   • 在 Telegram 中发送消息测试所有功能")
        print("   • Agent 可以使用所有工具和技能")
        print("   • 对话会自动保存和压缩")
        print("   • WebSocket 客户端可连接 ws://localhost:8765")
        print()
        print("按 Ctrl+C 停止服务")
        print()
        print("=" * 70)
        print()
        
        # 启动 Gateway
        await self.gateway.start(start_channels=True)
    
    async def stop(self) -> None:
        """停止服务器"""
        logger.info("⏹️  Stopping Full-Featured Server...")
        await self.gateway.stop()
        self.running = False
        logger.info("✅ Server stopped")


async def main():
    """主函数"""
    # 设置日志
    setup_logging(level="INFO", format_type="colored")
    
    print()
    print("🦞 OpenClaw Python - 完整功能启动")
    print("=" * 70)
    print()
    
    # 检查 API Key
    has_llm_key = any([
        os.getenv("ANTHROPIC_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("GOOGLE_API_KEY"),
    ])
    
    if not has_llm_key:
        print("❌ 错误: 未找到 LLM API key!")
        print("   请在 .env 中配置: ANTHROPIC_API_KEY, OPENAI_API_KEY, 或 GOOGLE_API_KEY")
        return
    
    # 创建配置
    config = ClawdbotConfig(
        gateway={
            "port": 8765,
            "bind": "loopback",
        },
        agent={
            "model": "gemini/gemini-3-flash-preview",
            "max_tokens": 4000,
        },
    )
    
    # 创建并启动服务器
    server = FullFeaturedServer(config)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n")
        await server.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
