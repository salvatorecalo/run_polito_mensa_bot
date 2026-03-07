
from services.notification_service import NotificationService
from services.scraper_service import fetch_and_store_menus
from utils import is_holiday
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def scheduled_task():
    """Task executed by scheduler"""
    try:
        logger.info("⏰ Starting scheduled task...")
        if is_holiday():
            logger.info("🎉 Today is a holiday! Skipping menu fetch and notifications.")
            return
        # 1. Fetch data from InstagramNavigator -> DB
        await fetch_and_store_menus()

        # 2. Send notifications from DB -> Telegram
        notifier = NotificationService()
        await notifier.send_daily_menu()

        logger.info("✅ Scheduled task completed")
    except Exception as e:
        logger.error(f"❌ Error in scheduled task: {e}", exc_info=True)