import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from bot.start_command import start_command
from bot.menu_command import menu_command
from bot.show_canteen_buttons import get_user_image_or_text_option, handle_canteen_toggle, handle_language_change, show_canteen_buttons, show_language_buttons
from database.repositories import UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

@inject_db
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    logger.info(f"🔵 handle_callback chiamato - session: {session is not None}")
    
    if not session or not update.callback_query: 
        logger.warning(f"❌ Session o callback_query mancante - session: {session is not None}, query: {update.callback_query is not None}")
        return
        
    query = update.callback_query
    await query.answer()
    
    data = query.data
    logger.info(f"🔵 Callback data ricevuto: {data}")
    
    if not data: return

    user_id = query.from_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(user_id)
    
    if not user: 
        logger.warning(f"❌ Utente {user_id} non trovato")
        return
    
    logger.info(f"✅ Utente trovato: {user.first_name} (ID: {user_id})")

    if data == "menu":
        logger.info("📍 Routing a menu_command")
        await menu_command(update, context)
    elif data == "subscribe_canteen":
        logger.info("📍 Routing a show_canteen_buttons")
        await show_canteen_buttons(update, context, session=session)
    elif data.startswith("toggle_canteen_"):
        c_id = data.split("_")[-1]
        if c_id.isdigit():
            logger.info(f"📍 Toggle mensa ID: {c_id}")
            await handle_canteen_toggle(update, context, session=session, canteen_id=int(c_id))
    elif data == "set_language":
        await show_language_buttons(update, context)
    elif data.startswith("lang_"):
        await handle_language_change(update, context, new_lang=data.split("_")[-1])
    elif data == "get_format":
        await get_user_image_or_text_option(update, context)
    elif data.startswith("set_format_"):
        user.image_or_text = data.split("_")[-1]
        await query.edit_message_text(f"✅ Formato impostato su: {user.image_or_text}")
        await asyncio.sleep(1)
        await start_command(update, context)
    elif data == "cancel":
        await user_repo.update_status(user_id, is_active=False)
        await query.edit_message_text("👋 Ti sei disiscritto correttamente. Invia /start per riscriverti di nuovo.")
    elif data == "start_back":
        await start_command(update, context)
