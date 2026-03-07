from telegram import Update
from telegram.ext import ContextTypes
from database.connection import get_session
from database.repositories import UserRepository

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
