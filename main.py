"""
Main entry point for the Polito Mensa Bot
"""

import asyncio
import logging
import signal
import sys

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.handlers import cancel_command, menu_command, start_command, subscribe_canteen, add_mensa, delete_mensa
from bot.scheduler import BotScheduler
from config import TELEGRAM_TOKEN
from database.connection import close_db, create_db_and_tables, get_session, init_db
from database.repositories import UserRepository
from services.notification_service import NotificationService
from services.scraper_service import fetch_and_store_menus
from utils.logger import setup_logger

# Setup Logger
logger = setup_logger(__name__)

# Global variables
scheduler = None
app = None


async def bot_added_to_group(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler when bot is added to a group"""
    chat = update.effective_chat
    if not chat:
        return

    async for session in get_session():
        repo = UserRepository(session)
        await repo.get_or_create(
            telegram_id=chat.id, first_name=chat.title or "Group", username=None
        )
        logger.info(f"📢 Bot added to group: {chat.title} ({chat.id})")

        if update.message:
            await update.message.reply_text(
                "👋 Ciao! Invierò qui i menu della mensa.\nUsa /start per configurare."
            )


async def handle_private_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler for private messages - auto register"""
    chat = update.effective_chat
    user = update.effective_user

    if chat and chat.type == "private" and user:
        async for session in get_session():
            repo = UserRepository(session)
            await repo.get_or_create(
                telegram_id=chat.id, first_name=user.first_name, username=user.username
            )


async def scheduled_task():
    """Task executed by scheduler"""
    try:
        logger.info("⏰ Starting scheduled task...")

        # 1. Fetch data from Instagram -> DB
        await fetch_and_store_menus()

        # 2. Send notifications from DB -> Telegram
        notifier = NotificationService()
        await notifier.send_daily_menu()

        logger.info("✅ Scheduled task completed")
    except Exception as e:
        logger.error(f"❌ Error in scheduled task: {e}", exc_info=True)


async def shutdown():
    """Graceful shutdown helper"""
    global scheduler
    logger.info("🧹 Performing cleanup...")

    if scheduler:
        scheduler.stop()

    await close_db()
    logger.info("👋 Goodbye!")


async def main():
    """Main Application Entry Point"""
    global scheduler, app

    logger.info("🚀 Starting Polito Mensa Bot...")

    try:
        # 1. Initialize Database
        await init_db()
        await create_db_and_tables()

        # 2. Setup Scheduler
        scheduler = BotScheduler()
        # Schedule task for 11:25 and 20:00 (approx)
        scheduler.add_daily_task(lambda: asyncio.create_task(scheduled_task()), 11, 25)
        scheduler.add_daily_task(lambda: asyncio.create_task(scheduled_task()), 20, 0)
        scheduler.start()

        # 3. Setup Telegram Bot
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN is not set in environment variables")

        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Register Handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("menu", menu_command))
        app.add_handler(CommandHandler("cancel", cancel_command))
        app.add_handler(CommandHandler("subscribe_canteen", subscribe_canteen))
        app.add_handler(CommandHandler("add_mensa", add_mensa))
        app.add_handler(CommandHandler("delete_mensa", delete_mensa))
        
        app.add_handler(
            ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER)
        )
        app.add_handler(
            MessageHandler(filters.ChatType.PRIVATE, handle_private_message)
        )

        # 4. Manual Start Lifecycle (Required for Async Main)
        logger.info("🤖 Initializing Bot...")
        await app.initialize()
        await app.start()


        if app.updater is None:
            raise RuntimeError("Telegram Updater is None (polling not possible)")

        logger.info("📡 Starting Polling...")
        await app.updater.start_polling(drop_pending_updates=True)

        # 5. Keep alive until signal
        stop_signal = asyncio.Future()

        def handle_signal():
            if not stop_signal.done():
                stop_signal.set_result(None)

        loop = asyncio.get_running_loop()

        # Cross-platform signal handling
        if sys.platform != "win32":
            loop.add_signal_handler(signal.SIGINT, handle_signal)
            loop.add_signal_handler(signal.SIGTERM, handle_signal)
        else:
            logger.warning("⚠️ Windows detected: Use Ctrl+C or kill process to stop.")
            # On Windows, we rely on the loop catching the KeyboardInterrupt in the run wrapper
            # or we can simple wait.

        try:
            # Wait here forever until signal is set
            await stop_signal
        except asyncio.CancelledError:
            pass

        logger.info("🛑 Stopping Bot...")

        # 6. Manual Stop Lifecycle
        if app.updater.running:
            await app.updater.stop()

        if app.running:
            await app.stop()
            await app.shutdown()

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        pass

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Handle Ctrl+C gracefully at the top level
