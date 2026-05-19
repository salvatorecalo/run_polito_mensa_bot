"""
Main entry point for the Polito Mensa Bot
"""
import os
import asyncio
import signal
import sys
from utils.schedule_task import scheduled_task
from utils.set_admins import set_admins
from telegram.ext import (
    ApplicationBuilder,
)
from bot.scheduler import BotScheduler
from config import TELEGRAM_TOKEN
from database.connection import create_db_and_tables, get_session, init_db
from database.repositories import CanteenRepository
from utils import define_all_handlers, setup_logger, setup_data_folder, shutdown

# Setup Logger
logger = setup_logger(__name__)

app = None
# Permission to create file executable in the vps with no problem (e.g. bot.db)
os.umask(0o007)

async def main():
    """Main Application Entry Point"""
    global scheduler, app
    logger.info("🚀 Starting Polito Mensa Bot...")
    loop = asyncio.get_running_loop()
    try:
        setup_data_folder()
        await init_db()
        await create_db_and_tables()
        scheduler = BotScheduler()
        # Schedule task for 11:45 and 18:30
        scheduler.add_daily_task(lambda: asyncio.run_coroutine_threadsafe(scheduled_task(), loop), 11, 45)
        scheduler.add_daily_task(lambda: asyncio.run_coroutine_threadsafe(scheduled_task(), loop), 18, 30)
        scheduler.start()
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN is not set in environment variables")
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        # Register Handlers (/command)
        define_all_handlers(app)
        logger.info("🤖 Initializing Bot...")
        await app.initialize()
        await app.start()
        await set_admins(["6638746092", "238016214", "322125458"])
        async for session in get_session():
             canteen_repo = CanteenRepository(session)
             canteens = await canteen_repo.get_all_active()
             if not canteens:
                logger.info("Canteens not found in db, so I'm recreating them...")
                await canteen_repo.initialize_all_canteens()  
        if app.updater is None:
            raise RuntimeError("Telegram Updater is None (polling not possible)")
        logger.info("📡 Starting Polling...")
        await app.updater.start_polling(drop_pending_updates=True)     
        stop_signal = asyncio.Future()
        def handle_signal():
            if not stop_signal.done():
                stop_signal.set_result(None)

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
