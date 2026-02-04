"""
Telegram Bot Handlers with Dependency Injection and Async Database Support
Uniformato per l'utilizzo esclusivo di bottoni e gestione robusta dei None
"""
import html
import os
import re
import asyncio
from datetime import datetime
from functools import wraps
from typing import Any, Callable
from services.scraper_service import fetch_and_store_menus
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from sqlmodel import select
from utils.translate_text import translate_text
from utils.logger import setup_logger
from database.connection import get_session_maker
from database.repositories import CanteenRepository, MenuRepository, UserRepository
from database.models import Canteen, Menu
from config.settings import CREATED_IMAGES_DIR
from utils.today import get_today_date

# Setup logger
logger = setup_logger(__name__)

# --- Dependency Injection Decorator ---

def inject_db(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if 'session' in kwargs:
            return await func(update, context, *args, **kwargs)
        if not update.effective_message:
            logger.error("Update.effective message was not found")
            return
        session_maker = get_session_maker()
        if not session_maker:
            logger.error("Session maker non inizializzato")
            return
            
        session = session_maker()
        try:
            result = await func(update, context, session=session, *args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            logger.error(f"❌ Database error in handler {func.__name__}: {e}", exc_info=True)
            await session.rollback()
            
            msg = update.effective_message or (update.callback_query.message if update.callback_query else None)
            if msg:
                await msg.reply_text("⚠️ Si è verificato un errore interno. Riprova più tardi.")
        finally:
            await session.close()
    return wrapper

# --- Core Logic Handlers (Standard Commands) ---

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
    
    keyboard = [
        [InlineKeyboardButton("🍽️ MENU DI OGGI", callback_data="menu")],
        [InlineKeyboardButton("📍 GESTISCI MENSE", callback_data="subscribe_canteen")],
        [InlineKeyboardButton("🌍 LINGUA", callback_data="set_language"), InlineKeyboardButton("🖼️ FORMATO", callback_data="get_format")],
        [InlineKeyboardButton("❌ DISISCRIVITI", callback_data="cancel")],
    ]
    
    translated = await translate_text(text, language)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(translated, reply_markup=reply_markup, parse_mode="HTML")
    elif update.effective_message:
        await update.effective_message.reply_text(translated, reply_markup=reply_markup, parse_mode="HTML")

@inject_db
async def debug_user_in_a_canteen(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    """Debug: mostra tutti gli utenti in una cantina"""
    if not session or not update.effective_message:
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
@inject_db
async def debug_menus(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    """Debug: mostra tutti i menu nel DB"""
    if not session or not update.effective_message:
        return
    
    canteen_repo = CanteenRepository(session)
    
    stmt = select(Menu).where(Menu.date == get_today_date())
    result = await session.execute(stmt)
    all_menus = result.scalars().all()
    
    msg = f"🔍 DEBUG - Menu salvati per {get_today_date()}:\n\n"
    
    if not all_menus:
        msg += "❌ Nessun menu trovato nel database!\n"
    else:
        for menu in all_menus:
            canteen = await canteen_repo.get_by_id(menu.canteen_id)
            msg += f"📍 {canteen.name if canteen else 'Unknown'}\n"
            msg += f"   ID Mensa: {menu.canteen_id}\n"
            msg += f"   Tipo: {menu.meal_type}\n"
            msg += f"   Data: {menu.date}\n"
            msg += f"   Testo: {menu.original_text[:100]}...\n\n"
    
    await update.effective_message.reply_text(msg)
    
@inject_db
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None) -> None:
    if not session or not update.effective_user or not context or not update.effective_message: return
    
    # Recuperiamo l'ID della chat in modo sicuro
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id: return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(update.effective_user.id)
    
    language = user.language if user else "it"
    
    # CONTROLLO MENSE - VERSIONE CORRETTA
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

    # RESTO DELLA LOGICA MENU
    logger.info(f"User selected canteens: {user.selected_canteen_ids}")

    
    meal_type = "lunch" if datetime.now().hour < 15 else "dinner"
    
    menu_repo = MenuRepository(session)
    canteen_repo = CanteenRepository(session)
    menus = await menu_repo.get_menus_by_date_for_canteens(get_today_date(), user.selected_canteen_ids, meal_type)
    
    if not menus:
        text = f"📅 Nessun menu disponibile per il {get_today_date().strftime('%d/%m')} ({meal_type}). Aspetta le 11:45 o le 19:00 di sera per riprovare."
        translated = await translate_text(text, language)
        await context.bot.send_message(chat_id=chat_id, text=translated)
        return

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

    if user.image_or_text == "text":
        await context.bot.send_message(chat_id=chat_id, text=response_text, parse_mode='HTML')
    else:
        os.makedirs(CREATED_IMAGES_DIR, exist_ok=True)

        for menu in menus:
            canteen = await canteen_repo.get_by_id(menu.canteen_id)
            if not canteen:
                continue

            menu_text = f"{canteen.name}\n\n{menu.original_text or 'Menu non disponibile'}"

            if language != "it":
                try:
                    trans = await translate_text(menu_text, dest_language=language)
                    if trans:
                        menu_text = trans
                except:
                    pass

# --- Callback Router ---

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
        await query.edit_message_text("👋 Ti sei disiscritto correttamente. Invia /start per tornare.")
    elif data == "start_back":
        await start_command(update, context)

# --- UI Builders (Sub-menus) ---

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

    common_langs = {
        'it': 'Italiano 🇮🇹',
        'en': 'English 🇬🇧',
        'es': 'Español 🇪🇸',
        'fr': 'Français 🇫🇷',
        'de': 'Deutsch 🇩🇪'
    }

    keyboard = [[InlineKeyboardButton(name, callback_data=f"lang_{code}")]
                for code, name in common_langs.items()]
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
    if not session or not update.callback_query or not new_lang: return
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
    
    keyboard = [
        [InlineKeyboardButton("📝 SOLO TESTO", callback_data="set_format_text")],
        [InlineKeyboardButton("🖼️ IMMAGINE", callback_data="set_format_image")],
        [InlineKeyboardButton("🔙 INDIETRO", callback_data="start_back")]
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

# --- Admin Commands (Gestione Database e Scraping) ---

@inject_db
async def refresh_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    if not session or not update.effective_user or not update.effective_message:
        return
    
    user_repo = UserRepository(session)
    # CORRETTO: await perché dobbiamo verificare se è admin
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ Comando riservato agli admin.")
        return

    # Risposta immediata a Telegram
    status_msg = await update.effective_message.reply_text(
        "🔄 Avvio aggiornamento menu...\nQuesta operazione potrebbe richiedere qualche minuto."
    )

    # Task lungo in background
    async def run_scraper():
        from database.connection import get_session_maker
        session_maker = get_session_maker()
        session_inner = session_maker()
        try:
            await fetch_and_store_menus()
            await status_msg.edit_text(
                "✅ Menu aggiornati con successo!\nUsa /menu per visualizzare i nuovi dati."
            )
        except Exception as e:
            logger.error(f"❌ Error during menu refresh: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Errore durante l'aggiornamento: {str(e)}")
        finally:
            await session_inner.close()
    asyncio.create_task(run_scraper())

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

@inject_db
async def delete_canteen(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    """Rimuove una mensa dal DB (Solo Admin). Formato: /delete_canteen Nome"""
    if not session or not update.effective_user or not update.effective_message:
        return

    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ Comando riservato agli admin.")
        return

    if not context.args:
        await update.effective_message.reply_text("⚠️ Usa: /delete_canteen Nome Esatto Mensa")
        return

    name = ' '.join(context.args).strip()
    canteen_repo = CanteenRepository(session)
    canteen = await canteen_repo.get_by_name(name)

    if not canteen or not canteen.id:
        await update.effective_message.reply_text(f"❌ Mensa '{name}' non trovata.")
        return

    try:
        await canteen_repo.delete(canteen.id)
        await update.effective_message.reply_text(f"✅ Mensa '{name}' eliminata.")
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Errore: {str(e)}")

@inject_db
async def switch_user_role(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    if not session or not update or not update.effective_user or not update.effective_message:
        return

    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text(
            "❌ Comando riservato agli admin."
        )
        return

    if not context.args:
        await update.effective_message.reply_text(
            "Sintassi errata: usa /add_admin [USER_ID]\nDove [USER_ID] è l'id dell'utente da rendere admin"
        )
        return
    
    new_admin_id = context.args[0]
    try:
        user = await user_repo.get_by_telegram_id((int(new_admin_id)))
        if not user:
            await update.effective_message.reply_text(
                f"✅ Utente non trovato"
            )
            return
        await user_repo.switch_user_role(int(new_admin_id))
        await update.effective_message.reply_text(
            f"✅ Utente {user.first_name} trovato e aggiornato"
        )
    except Exception as message:
        await update.effective_message.reply_text(
            repr(message)
        )
