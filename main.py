"""
Main entry point del bot Polito Mensa
"""

import asyncio
import os
import signal
import sys

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot import BotScheduler, cancel_command, help_command, start_command
from config import CREATED_IMAGES_DIR, DOWNLOAD_DIR, TELEGRAM_TOKEN
from core import download_and_send_stories
from data.subscribers import add_subscriber_async
from services import InstagramService
from utils.logger import setup_logger

# Import database
try:
    from database.connection import close_db, init_db

    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False

logger = setup_logger(__name__)

# Variabili globali per la gestione dello shutdown
scheduler = None
app = None
shutdown_event = asyncio.Event()

# Crea directory necessarie
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(CREATED_IMAGES_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)


async def bot_added_to_group(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler quando il bot viene aggiunto a un gruppo"""
    chat = update.effective_chat

    if chat:
        await add_subscriber_async(chat.id, chat.title)

        if update.message:
            await update.message.reply_text(
                "👋 Grazie per avermi aggiunto al gruppo!\n\n"
                "Invierò automaticamente i menu delle mense Edisu ogni giorno.\n"
                "Per interrompere il servizio, rimuovimi dal gruppo."
            )

        logger.info(f"📢 Bot aggiunto al gruppo: {chat.title or chat.id}")


async def handle_private_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handler per messaggi privati - iscrive automaticamente l'utente"""
    chat = update.effective_chat

    if chat and chat.type == "private":
        user = update.effective_user
        username = user.username if user else None

        await add_subscriber_async(chat.id, username)

        if update.message:
            await update.message.reply_text(
                "👋 Ti ho iscritto automaticamente!\n\n"
                "Riceverai i menu ogni giorno alle 11:25 e 20:00.\n"
                "Usa /cancel per disiscriverti o /help per info."
            )

        logger.info(f"📩 Utente privato iscritto: {chat.id}")


async def scheduled_task(cl):
    """Task eseguito dallo scheduler agli orari configurati"""
    try:
        logger.info("⏰ Esecuzione schedulata avviata")
        await download_and_send_stories(cl)
        logger.info("✅ Esecuzione schedulata completata")
    except Exception as e:
        logger.error(f"❌ Errore durante esecuzione schedulata: {e}")
        import traceback

        traceback.print_exc()


def signal_handler(signum, frame):
    """Gestisce i segnali di interruzione (Ctrl+C, SIGTERM)"""
    signal_name = signal.Signals(signum).name
    logger.info(f"🛑 Ricevuto segnale {signal_name}, avvio shutdown...")
    shutdown_event.set()


async def shutdown():
    """Esegue la chiusura pulita di tutte le componenti"""
    global scheduler

    logger.info("🧹 Pulizia risorse in corso...")

    # Ferma lo scheduler
    if scheduler:
        logger.info("⏸️ Fermando scheduler...")
        scheduler.stop()
        logger.info("✅ Scheduler fermato")

    # Close database
    if DATABASE_AVAILABLE:
        await close_db()

    logger.info("👋 Shutdown completato con successo")


async def main():
    """Entry point principale dell'applicazione"""
    global scheduler, app

    logger.info("🚀 Avvio Bot Polito Mensa...")

    try:
        # Initialize database
        if DATABASE_AVAILABLE:
            logger.info("🗄️ Initializing database...")
            await init_db()
            logger.info("✅ Database ready")
        else:
            logger.warning("⚠️ Database not available, using JSON storage")

        # Login Instagram
        logger.info("🔑 Login a Instagram in corso...")
        try:
            ig_service = InstagramService()
            cl = ig_service.login()
            logger.info("✅ Login Instagram completato")
        except Exception as e:
            logger.error(f"❌ Errore login Instagram: {e}")
            import traceback

            traceback.print_exc()
            return

        # Esecuzione immediata al primo avvio
        logger.info("📸 Esecuzione iniziale...")
        try:
            await download_and_send_stories(cl)
            logger.info("✅ Esecuzione iniziale completata")
        except Exception as e:
            logger.error(f"❌ Errore esecuzione iniziale: {e}")
            import traceback

            traceback.print_exc()

        # Setup scheduler
        scheduler = BotScheduler()
        scheduler.add_default_schedules(lambda: asyncio.create_task(scheduled_task(cl)))
        scheduler.start()

        # Setup bot Telegram
        if not TELEGRAM_TOKEN:
            logger.error("❌ TELEGRAM_TOKEN non configurato")
            return

        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

        # Aggiungi handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("cancel", cancel_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(
            ChatMemberHandler(bot_added_to_group, ChatMemberHandler.MY_CHAT_MEMBER)
        )
        app.add_handler(
            MessageHandler(filters.ChatType.PRIVATE, handle_private_message)
        )

        logger.info("🤖 Bot Telegram in esecuzione... (Premi Ctrl+C per fermare)")

        # Avvia polling con gestione interruzione integrata
        try:
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                stop_signals=[signal.SIGINT, signal.SIGTERM],
                close_loop=False,  # Non chiudere il loop automaticamente
            )
        except KeyboardInterrupt:
            logger.info("⏹️ Interruzione da tastiera ricevuta")

    except Exception as e:
        logger.error(f"❌ Errore fatale: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Esegui shutdown pulito
        await shutdown()


if __name__ == "__main__":
    try:
        import nest_asyncio

        nest_asyncio.apply()
    except ImportError:
        logger.warning(
            "⚠️ nest_asyncio non installato - potrebbe causare problemi con Jupyter"
        )

    asyncio.run(main())
