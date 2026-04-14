from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from database.repositories import UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger
from utils.translate_text import translate_text

logger = setup_logger(__name__)

@inject_db
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None) -> None:
    if not session or not update.effective_user: return
    
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=update.effective_user.id, 
        first_name=update.effective_user.first_name, 
        username=update.effective_user.username
    )
    
    if not user: return

    # Riattiva se era disattivato
    if not user.is_active:
        await user_repo.update_status(user.telegram_id, is_active=True)

    language = user.language
    text = f"👋 Ciao {user.first_name}! Benvenuto nel bot della mensa del PoliTo.\n\nUsa i pulsanti qui sotto per gestire il tuo profilo e vedere il menu."
    language = user.language
    translated_messages = [
        await translate_text("🍽️ MENU DI OGGI", language),
        await translate_text("📍 GESTISCI MENSE", language),
        await translate_text("🌍 LINGUA", language),
        await translate_text("🖼️ FORMATO", language),
        await translate_text("❌ DISISCRIVITI", language)
    ]

    keyboard = [
        [InlineKeyboardButton(translated_messages[0], callback_data="menu")],
        [InlineKeyboardButton(translated_messages[1], callback_data="subscribe_canteen")],
        [InlineKeyboardButton(translated_messages[2], callback_data="set_language"), InlineKeyboardButton(translated_messages[3], callback_data="get_format")],
        [InlineKeyboardButton(translated_messages[4], callback_data="cancel")],
    ]
    
    translated = await translate_text(text, language)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(translated, reply_markup=reply_markup, parse_mode="HTML")
    elif update.effective_message:
        await update.effective_message.reply_text(translated, reply_markup=reply_markup, parse_mode="HTML")
