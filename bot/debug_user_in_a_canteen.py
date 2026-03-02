from asyncio.log import logger
from telegram import Update
from telegram.ext import ContextTypes
from database.repositories import CanteenRepository, UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

@inject_db
async def debug_user_in_a_canteen(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    """Debug: mostra tutti gli utenti in una cantina"""
    if not session or not update.effective_message or not update.effective_user:
        logger.error("Nessuna sessione trovata")
        return
    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text(
            "❌ Comando riservato agli admin."
        )
        return
    if not context.args:
        await update.effective_message.reply_text("⚠️ Specifica l'ID della mensa. Esempio: /debug_canteen 1")
        return
    
    try:
        canteen_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("❌ L'ID deve essere un numero intero.")
        return
    
    user_repo = UserRepository(session)
    canteen_repo = CanteenRepository(session)
    canteen = await canteen_repo.get_by_id(canteen_id)
    if not canteen:
        await update.effective_message.reply_text(f"❓ Mensa con ID {canteen_id} non trovata.")
        return

    users = await user_repo.get_users_by_canteen(canteen_id)
    if not users:
        await update.effective_message.reply_text(f"📍 Nessun utente iscritto alla mensa: **{canteen.name}**")
        return 
    
    response = f"👥 **Utenti iscritti a {canteen.name}:**\n\n"
    for u in users:
        username = f"(@{u.username})" if u.username else ""
        response += f"• {u.first_name} {username} [ID: `{u.telegram_id}`]\n"

    await update.effective_message.reply_text(response, parse_mode="Markdown")