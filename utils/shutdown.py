
from database.connection import close_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

scheduler = None

async def shutdown():
    """Graceful shutdown helper"""
    global scheduler
    logger.info("🧹 Performing cleanup...")

    if scheduler:
        scheduler.stop()

    await close_db()
    logger.info("👋 Goodbye!")
