from telegram import Update
from telegram.ext import ContextTypes

from database.models import Canteen
from database.repositories import CanteenRepository, UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

@inject_db
async def add_canteen(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    """Aggiunge una mensa al DB (Solo Admin). Formato: /add_canteen Nome | Indirizzo"""
    if not session or not update.effective_user or not update.effective_message:
        return

    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ Comando riservato agli admin.")
        return

    if not context.args:
        await update.effective_message.reply_text("⚠️ Usa: /add_canteen Nome Mensa | Indirizzo")
        return

    full_text = ' '.join(context.args)
    if '|' not in full_text:
        await update.effective_message.reply_text("⚠️ Formato errato. Usa il separatore '|'.")
        return

    parts = full_text.split('|', 1)
    name = parts[0].strip()
    location = parts[1].strip()

    canteen_repo = CanteenRepository(session)
    new_canteen = Canteen(name=name, location_description=location)
    try:
        await canteen_repo.create(new_canteen)
        await update.effective_message.reply_text(f"✅ Mensa '{name}' aggiunta con successo.")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Errore: {str(e)}")