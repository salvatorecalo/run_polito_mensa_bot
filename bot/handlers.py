"""
Telegram Bot Handlers with Dependency Injection and Async Database Support
"""
import html
from utils.logger import setup_logger
from datetime import date, datetime, timezone
from functools import wraps
from typing import Any, Callable
import os
from googletrans import Translator, LANGUAGES
from telegram import Update
from telegram.ext import ContextTypes
import re

from utils.image_processing import create_long_image
from database.connection import get_session_maker
from database.repositories import CanteenRepository, MenuRepository, UserRepository
from database.models import Canteen

from config.settings import ADMIN_IDS, CREATED_IMAGES_DIR 

# Setup logger
logger = setup_logger(__name__)

# Setup translator
translator = Translator()

# --- Dependency Injection Decorator ---

def inject_db(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to inject a database session into the handler.
    Manages the session lifecycle (open/close) and basic error handling.
    """

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        session_maker = get_session_maker()
        session = session_maker()
        try:
            result = await func(update, context, session=session, *args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            logger.error(
                f"❌ Database error in handler {func.__name__}: {e}", exc_info=True
            )
            await session.rollback()
            
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Si è verificato un errore interno. Riprova più tardi."
                )
        finally:
            await session.close()

    return wrapper

# --- Helper Functions ---

async def translate_text(text: str, dest_language: str) -> str:
    """
    Translate text to destination language, preserving commands
    
    Args:
        text: Text to translate (in Italian)
        dest_language: Destination language code
    
    Returns:
        Translated text with commands preserved
    """
    try:
        if dest_language == "it":
            return text
        
        # 1. Trova tutti i comandi (pattern: /comando)
        command_pattern = r'(/[a-zA-Z_]+)'
        commands = re.findall(command_pattern, text)
        
        # 2. Sostituisci i comandi con placeholder
        text_with_placeholders = text
        placeholders = {}
        for i, command in enumerate(commands):
            placeholder = f"__CMD{i}__"
            placeholders[placeholder] = command
            text_with_placeholders = text_with_placeholders.replace(command, placeholder, 1)
        
        # 3. Traduci il testo con i placeholder
        result = await translator.translate(text_with_placeholders, dest=dest_language, src='it')
        translated_text = result.text
        
        # 4. Ripristina i comandi originali
        for placeholder, command in placeholders.items():
            translated_text = translated_text.replace(placeholder, command)
        
        return translated_text
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text  # Fallback to original text

# --- Handlers ---


@inject_db
async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
) -> None:
    """Handler for /start. Registers the user in the database."""
    if not update.effective_user or not update.effective_chat or not update.effective_message:
        return

    if session is None:
        logger.error("Session is None in start_command")
        return

    user_data = update.effective_user
    logger.info(f"📝 /start command received from {user_data.id}")

    try:
        repo = UserRepository(session)
        user = await repo.get_or_create(
            telegram_id=user_data.id,
            first_name=user_data.first_name,
            username=user_data.username,
        )

        language = user.language

        if not user.is_active:
            await repo.update_status(user.telegram_id, is_active=True)
            text = "👋 Bentornato! Ti ho riattivato il servizio notifiche."
            translated = await translate_text(text, language)
            await update.effective_message.reply_text(translated)
        else:
            text = (
                f"👋 Ciao {user.first_name}! Ti sei iscritto con successo.\n\n"
                "Riceverai i menu delle mense che configuri ogni giorno.\n"
                "Usa /menu per vedere il menu di oggi.\n"
                "Usa /cancel per disiscriverti.\n"
                "Usa /subscribe_canteen [NOME_MENSA] per ricevere i menù di quella mensa.\n"
                "Usa /unsubscribe_canteen [NOME_MENSA] per smettere di ricevere i menù di quella mensa.\n"
                "Puoi ricevere contemporaneamente il menù di più mense."
            )
            translated = await translate_text(text, language)
            await update.effective_message.reply_text(translated)

    except Exception as e:
        raise e

"""
Add this handler to your handlers.py file
"""

@inject_db
async def refresh_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """
    Force refresh menus from Instagram mirror (Admin only)
    """
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in refresh_menu command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🔄 /refresh_menu command received from {telegram_id}")
    user_repo = UserRepository(session)
    language = await user_repo.get_user_language(session, telegram_id)
    
    # Check if user is admin
    if telegram_id not in ADMIN_IDS:
        text = "❌ Non hai i permessi per eseguire questo comando."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    # Notify user that refresh is starting
    text = "🔄 Avvio aggiornamento menu...\nQuesta operazione potrebbe richiedere qualche minuto."
    translated = await translate_text(text, language)
    status_msg = await update.effective_message.reply_text(translated)
    
    try:
        # Import here to avoid circular imports
        from services.scraper_service import fetch_and_store_menus
        
        # Run scraper service
        await fetch_and_store_menus()
        
        # Success message
        text = "✅ Menu aggiornati con successo!\nUsa /menu per visualizzare i nuovi menu."
        translated = await translate_text(text, language)
        await status_msg.edit_text(translated)
        
    except Exception as e:
        logger.error(f"❌ Error during menu refresh: {e}", exc_info=True)
        text = f"❌ Errore durante l'aggiornamento: {str(e)}"
        translated = await translate_text(text, language)
        await status_msg.edit_text(translated)

@inject_db
async def menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
) -> None:
    """
    Handler for /menu command - Shows today's menu
    """
    if not update.effective_user or not update.effective_message:
        return

    if session is None:
        logger.error("Session is None in menu_command")
        return

    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /menu command received from {telegram_id}")

    try:
        logger.info("Step 1: Creating repository")
        user_repo = UserRepository(session)
        menu_repo = MenuRepository(session)
        canteen_repo = CanteenRepository(session)
        logger.debug("✓ Repositories created")

        logger.debug(f"Step 2: Getting user {telegram_id}...")
        user = await user_repo.get_by_telegram_id(telegram_id)
        logger.debug(f"Obtained user {user}")
        
        if not user:
            text = "⚠️ Non sei registrato. Usa /start prima."
            await update.effective_message.reply_text(text)
            return

        logger.debug(f"Step 3: Getting user language and canteens...")
        language = user.language  # User's preferred language
        canteen_ids = user.selected_canteen_ids
        logger.debug(f"✓ Language: {language}, Canteen IDs: {canteen_ids}")

        if not canteen_ids:
            text = "⚠️ Non sei iscritto a nessuna mensa.\nUsa /subscribe_canteen per iscriverti."
            translated = await translate_text(text, language)
            await update.effective_message.reply_text(translated, parse_mode='HTML')
            return

        today = date.today()
        current_hour = datetime.now().hour
        meal_type = "lunch" if current_hour < 15 else "dinner"
        logger.debug(f"✓ Date: {today}, Meal type: {meal_type}")

        logger.info("Cercando i menù nei repository")
        import asyncio
        try:
            menus = await asyncio.wait_for(
                menu_repo.get_menus_by_date_for_canteens(
                    today, canteen_ids, meal_type
                ),
                timeout=10.0
            )
            logger.info(f"✓ Menus retrieved: {len(menus)} found")
        except asyncio.TimeoutError:
            logger.error("❌ TIMEOUT: Query took more than 10 seconds!")
            await update.effective_message.reply_text("⚠️ Errore: timeout database. Riprova.")
            return
        
        if not menus:
            logger.warning(f"No menus found for canteens {canteen_ids} on {today}")
            text = (
                f"📅 Menu del {today.strftime('%d/%m/%Y')} ({meal_type})\n\n"
                "❌ Menu non ancora disponibile per le tue mense.\n\n"
                "I menu vengono aggiornati automaticamente:\n"
                "🕐 ore 11:25 (pranzo)\n"
                "🕗 ore 20:00 (cena)\n\n"
                "Riprova tra qualche minuto! ⏰"
            )
            translated = await translate_text(text, language)
            await update.effective_message.reply_text(translated, parse_mode='HTML')
            return

        logger.info(f"Building response for {len(menus)} menus")
        
        # Build response with menus
        response_text = f"🍽️ Menu del {today.strftime('%d/%m/%Y')} ({meal_type})\n\n"
        
        for menu in menus:
            canteen = await canteen_repo.get_by_id(menu.canteen_id)
            if not canteen:
                continue
            
            # Add canteen header (always visible)
            canteen_name = canteen.name.replace("_", " ")
            canteen_location = canteen.location_description.strip('"')
            response_text += f"📍 <b>{html.escape(canteen_name)}</b>\n"
            response_text += f"   <i>{html.escape(canteen_location)}</i>\n\n"
            
            # Get menu text (original Italian)
            menu_text = menu.original_text if menu.original_text else ""
            
            # Translate menu on-demand if user language is not Italian
            if language != "it" and menu_text:
                try:
                    logger.debug(f"Translating menu from Italian to {language}")
                    result = await translator.translate(menu_text, src="it", dest=language)
                    menu_text = result.text
                    logger.info(f"🌐 Menu translated to {language}")
                except Exception as e:
                    logger.error(f"Translation error: {e}")
                    # Fallback to Italian if translation fails
                    menu_text = menu.original_text
            
            # CRITICAL: Escape HTML characters to prevent parse errors
            menu_text_escaped = html.escape(menu_text)
            
            response_text += menu_text_escaped + "\n\n"
            response_text += "─" * 30 + "\n\n"

        # Add timestamp footer
        timestamp = datetime.now(timezone.utc).strftime('%H:%M')
        footer_text = f"Ultimo aggiornamento: {timestamp}"
        
        # Translate footer if needed
        if language != "it":
            try:
                footer_translated = await translate_text(footer_text, language)
                footer_text = footer_translated
            except Exception as e:
                logger.error(f"Footer translation error: {e}")
                # Keep Italian if translation fails
        
        response_text += f"<i>{html.escape(footer_text)}</i>"

        logger.debug("Sending response to user")
        # QUI
        if user.image_or_text == "text":
            await update.effective_message.reply_text(response_text, parse_mode='HTML')
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"menu_{telegram_id}_{timestamp}.jpg"
            image_path = os.path.join(CREATED_IMAGES_DIR, filename)
            os.makedirs(CREATED_IMAGES_DIR, exist_ok=True)
            
            try:
                clean_text = html.unescape(re.sub(r'<[^>]+>', '', response_text))
                created_image_path = create_long_image(
                    text=clean_text,
                    output_path=image_path
                )
                with open(created_image_path, 'rb') as photo:
                    await update.effective_message.reply_photo(
                        photo=photo,
                        caption=f"🍽️ Menu del {today.strftime('%d/%m/%Y')} ({meal_type})"
                    )      
            except Exception as e:
                logger.error(f"Error creating/sending image: {e}", exc_info=True)
                # Fallback al testo se l'immagine fallisce
                await update.effective_message.reply_text(response_text, parse_mode='HTML')
                
        
    except Exception as e:
        logger.error(f"❌ Error in menu_command: {e}", exc_info=True)
        
        # Fallback error message
        error_msg = "⚠️ Si è verificato un errore interno. Riprova più tardi."
        try:
            if language != "it":
                error_msg = await translate_text(error_msg, language)
        except:
            pass  # Keep Italian if translation fails
        
        await update.effective_message.reply_text(error_msg)
@inject_db
async def cancel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
) -> None:
    """Handler for /cancel. Deactivates the user."""
    if not update.effective_user or not update.effective_message:
        return

    if session is None:
        logger.error("Session is None in cancel_command")
        return

    telegram_id = update.effective_user.id
    repo = UserRepository(session)
    
    language = await repo.get_user_language(session, telegram_id)
    success = await repo.update_status(telegram_id, is_active=False)

    if success:
        text = "👋 Ti sei disiscritto correttamente.\nNon riceverai più notifiche automatiche."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
    else:
        text = "ℹ️ Non eri iscritto."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)


@inject_db
async def subscribe_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Subscribe a specific user to a canteen"""
    
    if not update.effective_user or not update.effective_message:
        return

    if session is None:
        logger.error("Session is None in subscribe_canteen command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /subscribe_canteen command received from {telegram_id}")

    user_repo = UserRepository(session)
    canteen_repo = CanteenRepository(session)
    
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        text = "⚠️ Non sei registrato. Usa /start prima."
        translated = await translate_text(text, "it")
        await update.effective_message.reply_text(translated)
        return
    
    language = user.language
    
    if not context.args:
        text = "⚠️ Devi specificare il nome della mensa.\nEsempio: /subscribe_canteen Nome Mensa"
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    canteen_name = " ".join(context.args)
    canteen = await canteen_repo.get_by_name(canteen_name)
    
    if not canteen or canteen.id is None:
        all_canteens = await canteen_repo.get_all_active()
        text = f"❌ Mensa '{canteen_name}' non trovata nel database.\n\nDevi inserire una di queste mense:"
        translated = await translate_text(text, language)
        msg = f"<b>{translated}</b>\n\n"
        
        for c in all_canteens:
            msg += f"📍 <b>{c.name}</b>\n   <i>{c.location_description}</i>\n\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
        return 
    
    canteen_id: int = canteen.id
    success = await user_repo.add_canteen_to_user(telegram_id, canteen_id)
    
    if success:
        user_canteen_ids = await user_repo.get_user_canteens(telegram_id)
        
        text = f"✅ Iscritto con successo alla mensa {canteen.name}!\n\n📋 Sei iscritto a {len(user_canteen_ids)} mensa/e:\n"
        
        for cid in user_canteen_ids:
            c = await canteen_repo.get_by_id(cid)
            if c:
                text += f"  • {c.name}\n"
        
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
    else:
        text = f"ℹ️ Sei già iscritto alla mensa {canteen.name}."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')

@inject_db
async def unsubscribe_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Unsubscribe a specific user from a canteen"""
    
    if not update.effective_user or not update.effective_message:
        return

    if session is None:
        logger.error("Session is None in unsubscribe_canteen command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /unsubscribe_canteen command received from {telegram_id}")

    user_repo = UserRepository(session)
    canteen_repo = CanteenRepository(session)
    
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if not user:
        text = "⚠️ Non sei registrato. Usa /start prima."
        translated = await translate_text(text, "it")
        await update.effective_message.reply_text(translated)
        return
    
    language = user.language
    
    if not context.args:
        text = "⚠️ Devi specificare il nome della mensa.\nEsempio: /unsubscribe_canteen Nome Mensa"
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    canteen_name = " ".join(context.args)
    canteen = await canteen_repo.get_by_name(canteen_name)
    
    if not canteen or canteen.id is None:
        all_canteens = await canteen_repo.get_all_active()
        text = f"❌ Mensa '{canteen_name}' non trovata nel database.\n\nDevi inserire una di queste mense:"
        translated = await translate_text(text, language)
        msg = f"<b>{translated}</b>\n\n"
        
        for c in all_canteens:
            msg += f"📍 <b>{c.name}</b>\n   <i>{c.location_description}</i>\n\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
        return
    
    canteen_id: int = canteen.id
    success = await user_repo.remove_canteen_from_user(telegram_id, canteen_id)
    
    if success:
        user_canteen_ids = await user_repo.get_user_canteens(telegram_id)
        
        text = f"✅ Disiscritto correttamente da {canteen.name}.\n\n"
        
        if user_canteen_ids:
            text += f"📋 Sei ancora iscritto a {len(user_canteen_ids)} mensa/e:\n"
            for cid in user_canteen_ids:
                c = await canteen_repo.get_by_id(cid)
                if c:
                    text += f"  • {c.name}\n"
        else:
            text += "ℹ️ Non sei più iscritto a nessuna mensa."
        
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
    else:
        text = f"⚠️ Non eri iscritto alla mensa {canteen.name}."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')

# --- ADMIN COMMANDS ---

@inject_db
async def add_mensa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Admin command to add a new canteen - inline version with separator"""
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the add_mensa command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /add_mensa command received from {telegram_id}")
    user_repo = UserRepository(session)
    language = await user_repo.get_user_language(session, telegram_id)
    
    # Check admin
    if telegram_id not in ADMIN_IDS:
        text = "❌ Non hai i permessi per eseguire questo comando."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    # Parse con separatore "|" o ","
    if not context.args:
        text = (
            "⚠️ <b>Sintassi corretta:</b>\n\n"
            "/add_mensa Nome Mensa | Indirizzo completo\n\n"
            "<b>Esempi:</b>\n"
            "• /add_mensa Mensa Centrale | Torino, Campus Luigi Einaudi\n"
            "• /add_mensa Palazzo Nuovo | Via Sant'Ottavio 20, Torino\n"
            "• /add_mensa Biotecnologie | Via Nizza 52"
        )
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
        return
    
    # Unisci tutti gli argomenti
    full_text = ' '.join(context.args)
    
    # Splitta usando "|" come separatore
    if '|' not in full_text:
        text = (
            "⚠️ <b>Formato non valido!</b>\n\n"
            "Usa il simbolo <b>|</b> per separare nome e indirizzo:\n"
            "/add_mensa Nome Mensa | Indirizzo"
        )
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
        return
    
    # Estrai nome e location
    parts = full_text.split('|', 1)  # Split solo sulla prima occorrenza
    name = parts[0].strip()
    location = parts[1].strip() if len(parts) > 1 else ''
    
    # Validazioni
    if not name or len(name) < 3:
        text = "⚠️ Il nome della mensa deve essere almeno 3 caratteri."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    if not location or len(location) < 5:
        text = "⚠️ L'indirizzo deve essere almeno 5 caratteri."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    # Verifica duplicati
    canteen_repo = CanteenRepository(session)
    existing = await canteen_repo.get_by_name(name)
    if existing:
        text = f"⚠️ La mensa <b>{name}</b> esiste già nel database."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
        return
    
    # Crea mensa
    new_canteen = Canteen(
        name=name,
        location_description=location
    )
    
    await canteen_repo.create(new_canteen)
    
    text = (
        f"✅ Mensa aggiunta con successo!\n\n"
        f"📍 <b>{name}</b>\n"
        f"🗺️ {location}"
    )
    translated = await translate_text(text, language)
    await update.effective_message.reply_text(translated, parse_mode='HTML')
    
    logger.info(f"✅ Canteen '{name}' created successfully")
    
@inject_db
async def delete_mensa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Admin command to delete a canteen"""
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the delete_mensa command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /delete_mensa command received from {telegram_id}")
    user_repo = UserRepository(session)
    language = await user_repo.get_user_language(session, telegram_id)
    
    if telegram_id not in ADMIN_IDS:
        logger.error("Messaggio /delete_mensa non inviato da un admin")
        text = "❌ Non hai i permessi per eseguire questo comando."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    if not context.args:
        text = (
            "⚠️ <b>Sintassi corretta:</b>\n\n"
            "/delete_mensa Nome Mensa \n\n"
            "<b>Esempio:</b>\n"
            "• /delete_mensa Mensa Centrale\n"
        )
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
        return
    
    # Unisci tutti gli argomenti
    name = ' '.join(context.args)
    
    # Validazioni
    if not name:
        text = "⚠️ Il nome della mensa deve essere almeno 3 caratteri."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return

    canteen_repo = CanteenRepository(session)
    existing = await canteen_repo.get_by_name(name)
    if not existing:
        text = f"⚠️ La mensa <b>{name}</b> non esiste nel database."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
        return
    
    success = await canteen_repo.delete(existing.id if existing.id != None else 1)
    
    if success:
        text = f"✅ Mensa {existing.name} eliminata correttamente."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated, parse_mode='HTML')
    else:
        text = "⚠️ Errore durante l'eliminazione della mensa."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)

@inject_db
async def print_all_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Show all available canteens"""
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the print_all_canteen command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /print_all_canteen command received from {telegram_id}")
    user_repo = UserRepository(session)
    language = await user_repo.get_user_language(session, telegram_id)
    canteen_repo = CanteenRepository(session)
    all_canteens = await canteen_repo.get_all_active()
    
    if not all_canteens:
        text = "⚠️ Nessuna mensa configurata nel database."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    text = "🍽️ Tutte le mense disponibili:\n\n"
    
    for canteen in all_canteens:
        canteen_name = canteen.name.replace("_", " ")
        text += f"📍 {canteen_name}\n"
        text += f"   {canteen.location_description.strip('"')}\n"
        translated_is_active_text = await translate_text(f"   Attiva? {'✅' if canteen.is_active else '❌'}", language)
        text += translated_is_active_text
        text += "\n\n"
    
    await update.effective_message.reply_text(text, parse_mode='HTML')


@inject_db
async def print_subscribed_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Show user's subscribed canteens"""
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the print_subscribed_canteen command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /print_subscribed_canteen command received from {telegram_id}")
    
    user_repo = UserRepository(session)
    canteen_repo = CanteenRepository(session)
    
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        text = "⚠️ Non sei registrato. Usa /start prima."
        translated = await translate_text(text, "it")
        await update.effective_message.reply_text(translated)
        return
    
    language = user.language
    
    if not user.selected_canteen_ids:
        text = "⚠️ Non sei iscritto a nessuna mensa.\nUsa /subscribe_canteen per iscriverti."
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
        return
    
    text = "🍽️ Le tue mense:\n\n"
    
    for canteen_id in user.selected_canteen_ids:
        canteen = await canteen_repo.get_by_id(canteen_id)
        if canteen:
            canteen_name = canteen.name.replace("_", " ")
            text += f"📍 {canteen_name}\n"
            text += f"   {canteen.location_description.strip('"')}\n"
            translated_is_active_text = await translate_text(f"   Attiva? {'✅' if canteen.is_active else '❌'}", language)
            text += translated_is_active_text
            text += "\n\n"
    
        
    await update.effective_message.reply_text(text, parse_mode='HTML')


@inject_db
async def set_language(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Set user's language preference"""
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in set_language command")
        return
        
    telegram_id = update.effective_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if user is None:
        await update.effective_message.reply_text(
            "Utente non trovato / User not found"
        )
        return
    
    current_language = user.language
    
    if not context.args or len(context.args) < 1:
        text = "⚠️ Sintassi: /set_language [CODICE_LINGUA]\nEsempio: /set_language en"
        translated = await translate_text(text, current_language)
        await update.effective_message.reply_text(translated)
        return
    
    language = context.args[0].lower()
        
    if language not in LANGUAGES:
        text = f"❌ Lingua non supportata.\nLingue disponibili: {', '.join(LANGUAGES)}"
        translated = await translate_text(text, current_language)
        await update.effective_message.reply_text(translated)
        return
    
    success = await user_repo.update_user_language(telegram_id, language)
    
    if success:
        text = f"✅ Lingua impostata correttamente a: {language}"
        translated = await translate_text(text, language)
        await update.effective_message.reply_text(translated)
    else:
        await update.effective_message.reply_text("Error / Errore")

@inject_db
async def set_user_image_or_text_option(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    if not update.effective_user or not update.effective_message:
        return 
    
    if not session:
        logger.error("No session in set_user_image_or_text_option")
        return
    
    userRepo = UserRepository(session)
    telegram_id = update.effective_user.id
    user = await userRepo.get_by_telegram_id(telegram_id)
    if not user:
        logger.error("No user found")
        return
    
    if not context.args:
        await update.effective_message.reply_text(
            "Devi specificare il comando nel formato /set_image_or_text [OPTION]\nDove [OPTION] può essere o <code>image</code> o <code>text</code>",
            parse_mode="HTML"
        )
        return
    newOption = context.args[0].lower()
    new_option_list = ["image", "text"]
    if newOption not in new_option_list:
        reply_text = "Opzione non valida\nPuoi scegliere solo tra "
        reply_text += ", ".join(new_option_list)
        await update.effective_message.reply_text(reply_text)
        return
    user.image_or_text = newOption
    await update.effective_message.reply_text("Hai impostato correttamente la nuova preferenza.")
     
@inject_db  
async def get_user_image_or_text_option(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None) -> None:
    if not update.effective_user or not update.effective_message:
        return
    
    if not session:
        logger.error("No session in set_user_image_or_text_option")
        return
    
    userRepo = UserRepository(session)
    telegram_id = update.effective_user.id
    user = await userRepo.get_by_telegram_id(telegram_id)
    if not user:
        logger.error("No user found")
        return

    await update.effective_message.reply_text(
        f"Attualmente hai impostato: <code>{user.image_or_text}</code>"
    "\nPer cambiare opzione scrivi /set_image_or_text_option [OPZIONE]\n"
    "Opzioni disponibili:\n- image\n-text",
    parse_mode="HTML")
        
    
  
