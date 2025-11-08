"""
Handler per i comandi del bot Telegram
"""
from telegram import Update
from telegram.ext import ContextTypes
from data.subscribers import add_subscriber, remove_subscriber
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler per il comando /start - iscrive l'utente agli aggiornamenti.
    """
    if not update.effective_chat or not update.message:
        return
    
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    logger.info(f"📝 Comando /start da chat_id={chat_id} (utente: {user.username if user else 'unknown'})")
    
    if add_subscriber(chat_id):
        await update.message.reply_text(
            "✅ Ti sei iscritto con successo!\n\n"
            "Riceverai i menu della mensa ogni giorno agli orari:\n"
            "🍝 11:25 (pranzo)\n"
            "🍕 20:00 (cena)"
        )
        logger.info(f"✅ Nuovo iscritto: {chat_id}")
    else:
        await update.message.reply_text(
            "ℹ️ Sei già iscritto!\n\n"
            "Continuerai a ricevere gli aggiornamenti automaticamente."
        )
        logger.info(f"ℹ️ Utente già iscritto: {chat_id}")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler per il comando /cancel - rimuove l'utente dagli aggiornamenti.
    """
    if not update.effective_chat or not update.message:
        return
    
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    logger.info(f"❌ Comando /cancel da chat_id={chat_id} (utente: {user.username if user else 'unknown'})")
    
    if remove_subscriber(chat_id):
        await update.message.reply_text(
            "👋 Ti sei disiscritto con successo.\n\n"
            "Non riceverai più aggiornamenti automatici.\n"
            "Puoi iscriverti di nuovo in qualsiasi momento con /start"
        )
        logger.info(f"❌ Iscritto rimosso: {chat_id}")
    else:
        await update.message.reply_text(
            "ℹ️ Non sei iscritto.\n\n"
            "Usa /start per iscriverti agli aggiornamenti."
        )
        logger.info(f"ℹ️ Utente non iscritto: {chat_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler per il comando /help - mostra i comandi disponibili.
    """
    if not update.effective_chat or not update.message:
        return
    
    help_text = (
        "🍽️ *Bot Menu Mensa Polito*\n\n"
        "*Comandi disponibili:*\n"
        "/start - Iscriviti agli aggiornamenti\n"
        "/cancel - Disiscriviti dagli aggiornamenti\n"
        "/help - Mostra questo messaggio\n\n"
        "*Orari invio automatico:*\n"
        "🍝 11:25 - Menu pranzo\n"
        "🍕 20:00 - Menu cena\n\n"
        "Il bot monitora le stories Instagram delle mense Edisu "
        "e invia automaticamente i menu tradotti in inglese."
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')
    logger.info(f"ℹ️ Comando /help da chat_id={update.effective_chat.id}")
