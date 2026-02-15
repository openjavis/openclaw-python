"""
Telegram 受限测试版本
⚠️ 安全配置：仅允许基本对话，禁用所有危险功能
"""

import asyncio
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# 加载环境变量
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class RestrictedTelegramBot:
    """
    受限的 Telegram Bot - 仅用于测试
    
    安全限制：
    - ❌ 禁用所有工具（bash, file_ops, browser, etc）
    - ❌ 禁用文件操作
    - ❌ 禁用系统命令
    - ❌ 禁用网络访问
    - ✅ 仅允许基本对话
    - ✅ 使用 Gemini 3 Flash Preview
    """
    
    def __init__(self, bot_token: str, gemini_api_key: str):
        self.bot_token = bot_token
        self.gemini_api_key = gemini_api_key
        self.app = None
        self.provider = None
        self.conversations = {}  # 存储会话历史
        
    async def setup(self):
        """初始化 bot 和 provider"""
        from openclaw.agents.providers import GeminiProvider
        
        # 初始化 Gemini provider（纯对话，无工具）
        self.provider = GeminiProvider(
            model="gemini-3-flash-preview",
            api_key=self.gemini_api_key
        )
        logger.info("✅ Gemini Provider 初始化成功（受限模式）")
        
        # 创建 Telegram application
        self.app = Application.builder().token(self.bot_token).build()
        
        # 添加消息处理器
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        logger.info("✅ Telegram Bot 初始化成功")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        处理接收到的消息
        
        安全措施：
        - 只进行对话，不执行任何工具
        - 没有文件访问权限
        - 没有系统命令权限
        - 没有网络工具权限
        """
        try:
            # 获取消息信息
            user = update.effective_user
            chat_id = update.effective_chat.id
            message_text = update.message.text
            
            logger.info(f"📨 收到消息 from {user.first_name} (ID: {user.id}): {message_text[:50]}...")
            
            # 显示"正在输入..."
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            # 获取或创建会话历史
            if chat_id not in self.conversations:
                self.conversations[chat_id] = []
            
            # 添加系统提示（第一次对话）
            messages = []
            if len(self.conversations[chat_id]) == 0:
                from openclaw.agents.providers.base import LLMMessage
                system_msg = LLMMessage(
                    role="system",
                    content=(
                        "你是 OpenClaw 测试助手。这是一个受限测试版本。\n\n"
                        "重要限制：\n"
                        "- ⚠️ 你没有执行任何命令的权限\n"
                        "- ⚠️ 你不能访问文件系统\n"
                        "- ⚠️ 你不能浏览网页\n"
                        "- ⚠️ 你不能执行代码\n\n"
                        "你只能：\n"
                        "- ✅ 进行友好的对话\n"
                        "- ✅ 回答一般性问题\n"
                        "- ✅ 提供建议和信息\n\n"
                        "请用中文回复，简洁友好。"
                    )
                )
                messages.append(system_msg)
            
            # 添加历史消息（最多保留最近5轮对话）
            history_limit = 10  # 5轮对话 = 10条消息
            recent_history = self.conversations[chat_id][-history_limit:]
            messages.extend(recent_history)
            
            # 添加当前用户消息
            from openclaw.agents.providers.base import LLMMessage
            user_msg = LLMMessage(role="user", content=message_text)
            messages.append(user_msg)
            
            # 调用 LLM（无工具，纯对话）
            response_parts = []
            async for response in self.provider.stream(
                messages,
                max_tokens=500,  # 限制输出长度
                temperature=0.7,
                # ⚠️ 关键：不传递任何工具参数
                tools=None,
                enable_search=False  # 禁用搜索
            ):
                if response.type == "text_delta":
                    response_parts.append(response.content)
                elif response.type == "error":
                    logger.error(f"❌ LLM 错误: {response.content}")
                    await update.message.reply_text(
                        "抱歉，处理消息时出错了。请稍后再试。"
                    )
                    return
            
            # 组合完整响应
            full_response = "".join(response_parts)
            
            if not full_response:
                full_response = "抱歉，我没有生成回复。请重试。"
            
            # 发送响应
            await update.message.reply_text(full_response)
            logger.info(f"✅ 发送响应 to {user.first_name}: {full_response[:50]}...")
            
            # 保存到会话历史
            self.conversations[chat_id].append(user_msg)
            assistant_msg = LLMMessage(role="assistant", content=full_response)
            self.conversations[chat_id].append(assistant_msg)
            
            # 限制历史记录大小（最多保留20条消息 = 10轮对话）
            if len(self.conversations[chat_id]) > 20:
                self.conversations[chat_id] = self.conversations[chat_id][-20:]
            
        except Exception as e:
            logger.error(f"❌ 处理消息时出错: {e}", exc_info=True)
            try:
                await update.message.reply_text(
                    "抱歉，发生了错误。这是一个测试版本，功能受限。"
                )
            except:
                pass
    
    async def start(self):
        """启动 bot"""
        logger.info("🚀 启动 Telegram Bot（受限测试模式）...")
        
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(
            allowed_updates=["message"],  # 只接收消息更新
            drop_pending_updates=True     # 忽略旧消息
        )
        
        logger.info("✅ Bot 运行中！")
        logger.info("📱 在 Telegram 中搜索你的 bot 并发送消息")
        logger.info("⚠️  权限限制：仅允许基本对话，无工具访问")
        logger.info("")
        logger.info("按 Ctrl+C 停止...")
    
    async def stop(self):
        """停止 bot"""
        logger.info("🛑 停止 Bot...")
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        logger.info("✅ Bot 已停止")


async def main():
    """主函数"""
    
    print()
    print("=" * 70)
    print("🦞 OpenClaw Python - Telegram 受限测试版本")
    print("=" * 70)
    print()
    
    # 读取配置
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    # 验证配置
    if not bot_token:
        print("❌ 错误: 未找到 TELEGRAM_BOT_TOKEN")
        print("   请在 .env 文件中配置 Telegram Bot Token")
        return
    
    if not gemini_api_key:
        print("❌ 错误: 未找到 GOOGLE_API_KEY 或 GEMINI_API_KEY")
        print("   请在 .env 文件中配置 Gemini API Key")
        return
    
    print(f"✅ Telegram Token: {bot_token[:10]}...{bot_token[-10:]}")
    print(f"✅ Gemini API Key: {gemini_api_key[:10]}...{gemini_api_key[-5:]}")
    print()
    
    print("⚠️  安全配置（受限测试模式）:")
    print("   ❌ 禁用所有工具")
    print("   ❌ 禁用文件操作")
    print("   ❌ 禁用系统命令")
    print("   ❌ 禁用浏览器")
    print("   ❌ 禁用 Google Search")
    print("   ✅ 仅允许基本对话")
    print()
    
    # 创建并启动 bot
    bot = RestrictedTelegramBot(bot_token, gemini_api_key)
    
    try:
        await bot.setup()
        await bot.start()
        
        # 保持运行
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print()
        print("收到停止信号...")
    except Exception as e:
        logger.error(f"❌ 运行错误: {e}", exc_info=True)
    finally:
        await bot.stop()
        print()
        print("=" * 70)
        print("✅ 测试完成")
        print("=" * 70)


if __name__ == "__main__":
    print()
    print("🔒 安全提醒:")
    print("   - 这是一个受限测试版本")
    print("   - 仅用于验证 Telegram 集成")
    print("   - 没有危险功能权限")
    print("   - 所有工具已禁用")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见！")
