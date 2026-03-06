
from asyncio.log import logger
from datetime import datetime
import html
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from database.repositories import CanteenRepository, MenuRepository, UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger
from utils.today import get_today_date
from utils.translate_text import translate_text

logger = setup_logger(__name__)

@inject_db
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None) -> None:
    if not session or not update.effective_user or not context or not update.effective_message: return
    # Recuperiamo l'ID della chat in modo sicuro
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id: 
        logger.error("No chat id found")
        return
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(update.effective_user.id)
    language = user.language if user else "it"

    if not user or not user.selected_canteen_ids:
        text = "⚠️ Non sei iscritto a nessuna mensa.\nSeleziona almeno una mensa per continuare."
        translated = await translate_text(text, language)
        keyboard = [
            [InlineKeyboardButton("📍 GESTISCI MENSE", callback_data="subscribe_canteen")],
            [InlineKeyboardButton("🔙 MENU PRINCIPALE", callback_data="start_back")]
        ]
        try:
            await update.effective_message.reply_text(
                translated,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
        return
    meal_type = "lunch" if datetime.now().hour < 15 else "dinner"
    menu_repo = MenuRepository(session)
    canteen_repo = CanteenRepository(session)
    
    menus = await menu_repo.get_menus_by_date_for_canteens(get_today_date(), user.selected_canteen_ids, meal_type)
    if not menus:
        text = f"📅 Nessun menu disponibile per il {get_today_date().strftime('%d/%m')} ({meal_type}). Aspetta le 11:45 di pomeriggio o le 19:00 di sera per riprovare."
        translated = await translate_text(text, language)
        await context.bot.send_message(chat_id=chat_id, text=translated)
        return
    if user.image_or_text == "text":
        response_text = f"🍽️ <b>Menu {get_today_date().strftime('%d/%m')} ({meal_type})</b>\n\n"
        for menu in menus:
            canteen = await canteen_repo.get_by_id(menu.canteen_id)
            if canteen:
                response_text += f"📍 <b>{html.escape(canteen.name)}</b>\n"
                menu_content = menu.original_text or "Menu vuoto"
                if language != "it":
                    try:
                        trans = await translate_text(menu_content, dest_language=language)
                        if trans: menu_content = trans
                    except: pass
                response_text += f"{html.escape(menu_content)}\n\n"
        await context.bot.send_message(chat_id=chat_id, text=response_text, parse_mode='HTML')
    else:
        for menu in menus:
            images_paths = menu.courses_json.get("image_paths", {}) if menu.courses_json else {}
            target_image_path = images_paths.get(language, menu.image_path)
            if target_image_path and os.path.exists(target_image_path):
                user = await user_repo.get_by_telegram_id(update.effective_user.id)
                translation = await translate_text(meal_type, language)
                with open(target_image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=chat_id, 
                        photo=photo,
                        caption=f"📍 Menu ({translation})"
                    )
            else:
                # Se l'immagine manca per qualche motivo, inviamo il testo come fallback
                translated_error_text = await translate_text(f"Immagine non trovata per lingua {language} nel menu {menu.id}, invio testo.", language)
                logger.warning(translated_error_text)
                menu_content = menu.original_text or "Menu vuoto"
                if language != "it":
                    trans = await translate_text(menu_content, dest_language=language)
                    if trans: menu_content = trans
                await context.bot.send_message(chat_id=chat_id, text=menu.original_text)