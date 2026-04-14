"""
Telegram Bot Handlers with Dependency Injection and Async Database Support
Uniformato per l'utilizzo esclusivo di bottoni e gestione robusta dei None
"""

import asyncio
from bot.start_command import start_command
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from config.constants import COMMON_LANGS
from utils.decorator import inject_db
from utils.translate_text import translate_text
from utils.logger import setup_logger
from database.repositories import CanteenRepository, UserRepository

# Setup logger
logger = setup_logger(__name__)

@inject_db
async def show_canteen_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    logger.info(f"🟢 show_canteen_buttons chiamato - session: {session is not None}")
    
    if not session:
        logger.error("❌ Session mancante in show_canteen_buttons")
        return
        
    if not update.callback_query:
        logger.error("❌ callback_query mancante")
        return
        
    if not update.effective_user:
        logger.error("❌ effective_user mancante")
        return

    user_repo = UserRepository(session)
    canteen_repo = CanteenRepository(session)

    user = await user_repo.get_by_telegram_id(update.effective_user.id)
    logger.info(f"🟢 Utente recuperato: {user.first_name if user else 'None'}")
    
    all_canteens = await canteen_repo.get_all_active()
    logger.info(f"🟢 Mense trovate: {len(all_canteens) if all_canteens else 0}")

    if not user:
        logger.error("❌ User non trovato")
        return
        
    if not all_canteens:
        logger.warning("⚠️ Nessuna mensa attiva trovata")
        await update.callback_query.edit_message_text(
            "⚠️ Nessuna mensa disponibile al momento.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 INDIETRO", callback_data="start_back")]])
        )
        return

    keyboard = []
    for c in all_canteens:
        status = "✅" if c.id in user.selected_canteen_ids else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {c.name}",
                callback_data=f"toggle_canteen_{c.id}"
            )
        ])
        logger.info(f"  - {status} {c.name} (ID: {c.id})")

    keyboard.append([InlineKeyboardButton("🔙 INDIETRO", callback_data="start_back")])

    text = "📍 Seleziona le mense per ricevere i menu giornalieri:"
    translated = await translate_text(text, user.language)

    logger.info(f"🟢 Tentativo di inviare messaggio con {len(keyboard)} bottoni")

    try:
        await update.callback_query.edit_message_text(
            translated,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info("✅ Messaggio inviato con successo")
    except BadRequest as e:
        if "Message is not modified" in str(e):
            logger.info("ℹ️ Messaggio non modificato (già identico)")
        else:
            logger.error(f"❌ BadRequest: {e}")
            raise
    except Exception as e:
        logger.error(f"❌ Errore imprevisto: {e}", exc_info=True)
        raise
    
@inject_db
async def handle_canteen_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None, canteen_id=None):
    if not session or not update.effective_user or canteen_id is None: return
    user_repo = UserRepository(session)
    if canteen_id in (await user_repo.get_user_canteens(update.effective_user.id)):
        await user_repo.remove_canteen_from_user(update.effective_user.id, canteen_id)
    else:
        await user_repo.add_canteen_to_user(update.effective_user.id, canteen_id)
    await show_canteen_buttons(update, context)

@inject_db
async def show_language_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    if not session or not update.callback_query or not update.effective_user:
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(update.effective_user.id)

    keyboard = [[InlineKeyboardButton(name, callback_data=f"lang_{code}")]
                for code, name in COMMON_LANGS.items()]
    keyboard.append([InlineKeyboardButton("🔙 INDIETRO", callback_data="start_back")])

    text = "🌍 Seleziona la tua lingua:"
    translated = await translate_text(text, user.language if user else "it")

    try:
        await update.callback_query.edit_message_text(
            translated,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise

@inject_db
async def handle_language_change(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None, new_lang=None):
    if not session or not update.callback_query or not new_lang or not update.effective_user: return
    user_repo = UserRepository(session)
    await user_repo.update_user_language(update.effective_user.id, new_lang)
    await update.callback_query.edit_message_text(f"✅ Lingua aggiornata: {new_lang}")
    await asyncio.sleep(1)
    await start_command(update, context)

@inject_db
async def get_user_image_or_text_option(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    if not session or not update.effective_user or not update.effective_message: return
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(update.effective_user.id)
    if not user:
        await update.effective_message.reply_text("❌ Utente non trovato.")
        return
    language = user.language
    translated_messages = [
        await translate_text("📝 SOLO TESTO", language), 
        await translate_text("🖼️ IMMAGINE", language), 
        await translate_text("🔙 INDIETRO", language)
    ]
    keyboard = [
        [InlineKeyboardButton(translated_messages[0], callback_data="set_format_text")],
        [InlineKeyboardButton(translated_messages[1], callback_data="set_format_image")],
        [InlineKeyboardButton(translated_messages[2], callback_data="start_back")]
    ]
    text = f"Attualmente ricevi il menu come: <b>{user.image_or_text.upper() if user else 'TEXT'}</b>\n\nCome preferisci riceverlo?"
    translated = await translate_text(text, user.language if user else "it")

    if update.callback_query:
        await update.callback_query.edit_message_text(translated, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    else:
        await update.effective_message.reply_text(translated, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

# --- Vecchi Comandi (Uniformati come Redirect ai Bottoni) ---

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_language_buttons(update, context)

async def subscribe_canteen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_canteen_buttons(update, context)

async def unsubscribe_canteen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_canteen_buttons(update, context)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_command(update, context)

async def set_user_image_or_text_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_user_image_or_text_option(update, context)

async def get_user_image_or_text_option_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await get_user_image_or_text_option(update, context)