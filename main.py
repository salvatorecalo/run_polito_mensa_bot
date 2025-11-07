import os
import asyncio
from datetime import datetime, timedelta
import pytz
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)
from functions.download_and_send_stories import download_and_send_stories
from functions import login_client
from config import *
from functions.subscribers import load_subscribers, save_subscribers
import traceback

# === Setup base ===
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
subscribers = load_subscribers()

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🪶 {msg}")

# === Comandi Telegram ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in subscribers:
        subscribers.append(chat.id)
        save_subscribers(subscribers)
        await update.message.reply_text("✅ Iscritto! Riceverai aggiornamenti giornalieri.")
        log(f"👤 Nuovo iscritto: {chat.id}")
    else:
        await update.message.reply_text("Sei già iscritto.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subscribers(subscribers)
        await update.message.reply_text("❌ Disiscritto con successo.")
    else:
        await update.message.reply_text("Non risultavi iscritto.")

async def bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.id not in subscribers:
        subscribers.append(chat.id)
        save_subscribers(subscribers)
        await update.message.reply_text("Grazie per avermi aggiunto al gruppo. Invierò ogni giorno i menu delle mense edisu. \n Per interrompere il servizio devi togliermi dal gruppo.")
        log(f"📢 Bot aggiunto al gruppo: {chat.title or chat.id}")

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private" and chat.id not in subscribers:
        subscribers.append(chat.id)
        save_subscribers(subscribers)
        await update.message.reply_text(
            "👋 Ti ho iscritto automaticamente alla mailing list.\n"
            "Riceverai aggiornamenti ogni giorno. Usa /cancel per disiscriverti."
        )
        log(f"📩 Utente privato aggiunto: {chat.id}")

# === SCHEDULER PERSONALIZZATO ===
async def scheduler(cl):
    tz = pytz.timezone("Europe/Rome")

    async def run_daily(hour, minute):
        """Esegue download_and_send_stories ogni giorno all'orario specificato."""
        while True:
            now = datetime.now(tz)
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()

            log(f"⏰ Prossima esecuzione alle {next_run.strftime('%H:%M')} (tra {wait_seconds/60:.1f} min)")
            await asyncio.sleep(wait_seconds)
            try:
                await download_and_send_stories(cl)
                log("✅ Download e invio completati")
            except Exception as e:
                log(f"❌ Errore durante il download: {e}")
                traceback.print_exc()

    # Avvia due scheduler paralleli
    asyncio.create_task(run_daily(11, 25)) 
    asyncio.create_task(run_daily(20, 0))


# === MAIN ===
async def main():
    log("🔑 Login a Instagram in corso...")
    try:
        cl = login_client.login_client()
        log("✅ Login Instagram completato")
    except Exception as e:
        log(f"❌ Errore login Instagram: {e}")
        traceback.print_exc()
        cl = None

    # Esegui subito una volta
    if cl:
        await download_and_send_stories(cl)

    # Avvia scheduler giornaliero
    if cl:
        asyncio.create_task(scheduler(cl))

    # Avvio bot Telegram
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(ChatMemberHandler(bot_added, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, handle_private_message))

    log("🤖 Bot Telegram in esecuzione...")
    await app.run_polling()


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
