from telegram import Update
from telegram.ext import ContextTypes
from database.repositories import UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

@inject_db
async def switch_user_role(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    if not session or not update or not update.effective_user or not update.effective_message:
        return

    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text(
            "❌ Comando riservato agli admin."
        )
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Sintassi errata: usa /add_admin [USER_ID]\nDove [USER_ID] è l'id dell'utente da rendere admin"
        )
        return
    
    new_admin_id = context.args[0]
    try:
        user = await user_repo.get_by_telegram_id((int(new_admin_id)))
        if not user:
            await update.effective_message.reply_text(
                f"Utente non trovato"
            )
            return
        await user_repo.switch_user_role(int(new_admin_id))
        await update.effective_message.reply_text(
            f"✅ Utente {user.first_name} trovato e aggiornato"
        )
    except Exception as message:
        await update.effective_message.reply_text(
            repr(message)
        )
