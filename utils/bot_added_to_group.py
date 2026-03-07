from telegram import Update
from telegram.ext import ContextTypes
from database.connection import get_session
from database.repositories import UserRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)

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
