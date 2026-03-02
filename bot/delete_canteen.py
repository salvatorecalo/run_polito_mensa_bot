from telegram import Update
from telegram.ext import ContextTypes

from database.repositories import CanteenRepository, UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

@inject_db
async def delete_canteen(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    """Rimuove una mensa dal DB (Solo Admin). Formato: /delete_canteen Nome"""
    if not session or not update.effective_user or not update.effective_message:
        return

    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ Comando riservato agli admin.")
        return

    if not context.args:
        await update.effective_message.reply_text("⚠️ Usa: /delete_canteen Nome Esatto Mensa")
        return

    name = ' '.join(context.args).strip()
    canteen_repo = CanteenRepository(session)
    canteen = await canteen_repo.get_by_name(name)

    if not canteen or not canteen.id:
        await update.effective_message.reply_text(f"❌ Mensa '{name}' non trovata.")
        return

    try:
        await canteen_repo.delete(canteen.id)
        await update.effective_message.reply_text(f"✅ Mensa '{name}' eliminata.")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Errore: {str(e)}")