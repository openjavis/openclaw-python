"""
Example 5: Telegram Bot with Agent

This example shows how to:
1. Setup enhanced Telegram channel
2. Connect agent to Telegram
3. Handle messages
4. Use automatic reconnection

Prerequisites:
1. Create a bot via @BotFather on Telegram
2. Get your bot token
3. Set TELEGRAM_BOT_TOKEN environment variable
"""

import asyncio
import os
from dotenv import load_dotenv  
load_dotenv()  # Load .env file if present 
from pathlib import Path

from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import SessionManager
from openclaw.channels.base import InboundMessage
from openclaw.channels.enhanced_telegram import EnhancedTelegramChannel
from openclaw.monitoring import setup_logging


async def main():
    """Run Telegram bot example"""

    # Setup logging
    setup_logging(level="INFO", format_type="colored")

    # Check for bot token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN environment variable not set")
        print("\nTo get a bot token:")
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot and follow instructions")
        print("3. Copy the bot token")
        print("4. Set environment variable: export TELEGRAM_BOT_TOKEN='your-token'")
        return

    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    print("🤖 ClawdBot Telegram Bot Example")
    print("=" * 50)

    # Create components
    runtime = AgentRuntime(
        model="gemini/gemini-3-flash-preview", enable_context_management=True, max_retries=3
    )

    session_manager = SessionManager(workspace)

    # Create Telegram channel
    telegram = EnhancedTelegramChannel()
    runtime.add_event_listener(telegram.on_event)

    # Message handler
    async def handle_message(message: InboundMessage):
        """Handle incoming Telegram message"""
        print(f"\n📨 Message from {message.sender_name}: {message.text}")

        # Get or create session for this chat
        session = session_manager.get_session(f"telegram-{message.chat_id}")

        try:
            # Process with agent
            response_text = ""
            async for event in runtime.run_turn(session, message.text):
                if event.type == "assistant":
                    delta = event.data.get("delta", {})
                    if "text" in delta:
                        response_text += delta["text"]

            # Send response back to Telegram
            if response_text:
                await telegram.send_text(
                    message.chat_id, response_text, reply_to=message.message_id
                )
                print(f"✅ Response sent ({len(response_text)} chars)")

        except Exception as e:
            print(f"❌ Error: {e}")
            await telegram.send_text(
                message.chat_id, f"Sorry, I encountered an error: {e}", reply_to=message.message_id
            )

    # Set message handler
    telegram.set_message_handler(handle_message)

    # Start channel
    print("\n🚀 Starting Telegram bot...")
    print("📱 Send a message to your bot on Telegram")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 50 + "\n")

    await telegram.start({"bot_token": bot_token})

    # Show connection status
    print("\n✅ Bot started!")
    print(f"   Connected: {telegram.is_connected()}")
    print(f"   Healthy: {telegram.is_healthy()}")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)

            # Show metrics every 30 seconds
            if telegram.get_metrics():
                metrics = telegram.get_metrics()
                if metrics.messages_received > 0:
                    print(f"\n📊 Messages received: {metrics.messages_received}")
                    print(f"   Messages sent: {metrics.messages_sent}")

    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping bot...")
        await telegram.stop()
        print("✅ Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
