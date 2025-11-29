"""
Telegram Bot Handlers with Dependency Injection and Async Database Support
"""

import logging
from datetime import date, datetime
from functools import wraps
from typing import Any, Callable

from telegram import Update
from telegram.ext import ContextTypes

from database.connection import get_session_maker
from database.repositories import CanteenRepository, MenuRepository, UserRepository
from database.models import Canteen

from config.settings import ADMIN_IDS
from config.constants import LINGUE_SUPPORTATE

# Setup logger
logger = logging.getLogger(__name__)


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
            await session.rollback()  # Rollback in caso di errore
            
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Si è verificato un errore interno. Riprova più tardi."
                )
        finally:
            # Chiudi sempre la sessione
            await session.close()

    return wrapper


# --- Handlers ---


@inject_db
async def start_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
) -> None:
    """
    Handler for /start. Registers the user in the database.
    """
    if not update.effective_user or not update.effective_chat:
        return

    if session is None:
        logger.error("Session is None in start_command")
        return

    user_data = update.effective_user

    logger.info(f"📝 /start command received from {user_data.id}")

    try:
        repo = UserRepository(session)

        # Check if user exists or create new one
        # Note: We use the Telegram ID. The chat_id is usually the same for private chats.
        user = await repo.get_or_create(
            telegram_id=user_data.id,
            first_name=user_data.first_name,
            username=user_data.username,
        )

        # If the user was inactive (previously unsubscribed), reactivate them
        if not user.is_active:
            await repo.update_status(user.telegram_id, is_active=True)
            if update.effective_message:
                await update.effective_message.reply_text(
                    "👋 Bentornato! Ti ho riattivato il servizio notifiche."
                )
        else:
            current_language = await get_current_language(update, context, session)
            if update.effective_message:
                await update.effective_message.reply_text(
                    f"👋 Ciao {user.first_name}! Ti sei iscritto con successo.\n\n"
                    "Riceverai i menu delle mense che configuri ogni giorno.\n"
                    "Usa /menu per vedere il menu di oggi.\n"
                    "Usa /cancel per disiscriverti.\n"
                    "Usa /subscribe_canteen [NOME_MENSA] per ricevere i menù di quella mensa.\n"
                    "Usa /unsubscribe_canteen [NOME_MENSA] per smettere di ricevere i menù di quella mensa.\n"
                    "Puoi ricevere contemporaneamente il menù di più mense \n"
                    f"Lingua impostata: {"🇮🇹" if current_language == "italiano" else "🇬🇧"}"
                )

    except Exception as e:
        # The decorator catches this, but we re-raise to ensure logging if needed
        raise e


@inject_db
async def menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
) -> None:
    """
    Handler for /menu. Fetches today's menu from the DB.
    Does NOT scrape in real-time.
    """
    if not update.effective_user or not update.effective_message:
        return

    if session is None:
        logger.error("Session is None in menu_command")
        return

    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /menu command received from {telegram_id}")

    user_repo = UserRepository(session)
    menu_repo = MenuRepository(session)
    canteen_repo = CanteenRepository(session)

    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Non sei registrato. Usa /start prima."
            )
        return

    # Default to canteen ID 1 if none selected (or handle selection logic)
    # In a real scenario, you might force them to choose a canteen first
    canteen_ids = user.selected_canteen_ids

    if not canteen_ids:
        await update.effective_message.reply_text(
            "⚠️ Non sei iscritto a nessuna mensa.\n"
            "Usa /subscribe_canteen per iscriverti.",
            parse_mode='HTML'
        )
        return

    # 2. Fetch Menu
    today = date.today()

    # Determine meal type based on time (Lunch < 15:00 <= Dinner)
    # Simple logic: if it's morning/early afternoon show lunch, else dinner
    current_hour = datetime.now().hour
    meal_type = "lunch" if current_hour < 15 else "dinner"

    menus = await menu_repo.get_menus_by_date_for_canteens(
        today, canteen_ids, meal_type
    )

    if not menus:
        await update.effective_message.reply_text(
            f"📅 <b>Menu del {today.strftime('%d/%m/%Y')} ({meal_type})</b>\n\n"
            "❌ Nessun menu disponibile per le tue mense.\n"
            "Riprova più tardi.",
            parse_mode='HTML'
        )
        return

    # ✅ Formatta la risposta per ogni menu
    response_text = f"🍽️ <b>Menu del {today.strftime('%d/%m/%Y')} ({meal_type})</b>\n\n"
    
    for menu in menus:
        canteen = await canteen_repo.get_by_id(menu.canteen_id)
        if not canteen:
            continue
        
        response_text += f"📍 <b>{canteen.name}</b>\n"
        response_text += f"   <i>{canteen.location_description}</i>\n\n"
        
        if menu.translated_text:
            response_text += menu.translated_text + "\n\n"
        else:
            courses = menu.courses_json
            if isinstance(courses, dict):
                for course_type, dishes in courses.items():
                    response_text += f"<b>{course_type.upper()}:</b>\n"
                    for dish in dishes:
                        response_text += f"  • {dish}\n"
                response_text += "\n"
        
        response_text += "─" * 30 + "\n\n"

    await update.effective_message.reply_text(
        response_text,
        parse_mode='HTML'
    )


@inject_db
async def cancel_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
) -> None:
    """
    Handler for /cancel. Deactivates the user.
    """
    if session is None:
        logger.error("Session is None in cancel_command")
        return

    if not update.effective_user:
        return

    telegram_id = update.effective_user.id
    repo = UserRepository(session)

    success = await repo.update_status(telegram_id, is_active=False)

    if success:
        if update.effective_message:
            await update.effective_message.reply_text(
                "👋 Ti sei disiscritto correttamente.\n"
                "Non riceverai più notifiche automatiche."
            )
    else:
        if update.effective_message:
            await update.effective_message.reply_text("ℹ️ Non eri iscritto.")

@inject_db
async def subscribe_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """
        This methods subscribe a specific user to a canteen
    """
    
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
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Non sei registrato. Usa /start prima."
            )
        return
    
    # Context.args contiene i dati del messaggio dell'utente
    if not context.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Devi specificare il nome della mensa.\n"
                "Esempio: /subscribe_canteen Nome Mensa"
            )
        return
    
    # The user write correctly the command 
    canteen_name = " ".join(context.args) if context.args else ""
    canteen = await canteen_repo.get_by_name(canteen_name)
    
    if not canteen or canteen.id is None:
        all_canteens = await canteen_repo.get_all_active()
        msg = (
            f"<b>❌ Mensa '{canteen_name}' non trovata nel database.</b>\n\n"
            "<i>Devi inserire una di queste mense:</i>\n\n"
        )
        for c in all_canteens:
            msg += f"📍 <b>{c.name}</b>\n   <i>{c.location_description}</i>\n\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
        return 
    
    if canteen.id is None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Errore: la mensa non ha un ID valido."
            )
        return
    
    canteen_id: int = canteen.id
    
    success = await user_repo.add_canteen_to_user(telegram_id, canteen_id)
    
    if success:
        # Mostra tutte le mense
        user_canteen_ids = await user_repo.get_user_canteens(telegram_id)
        
        msg = f"✅ Iscritto con successo alla mensa <b>{canteen.name}</b>!\n\n"
        msg += f"📋 <b>Sei iscritto a {len(user_canteen_ids)} mensa/e:</b>\n"
        
        for cid in user_canteen_ids:
            c = await canteen_repo.get_by_id(cid)
            if c:
                msg += f"  • {c.name}\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
    else:
        await update.effective_message.reply_text(
            f"ℹ️ Sei già iscritto alla mensa <b>{canteen.name}</b>.",
            parse_mode='HTML'
        )

@inject_db
async def unsubscribe_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """
        This methods unsubscribe a specific user to a canteen
    """
    
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
        await update.effective_message.reply_text(
            "⚠️ Non sei registrato. Usa /start prima."
        )
        return
    
    # Context.args contiene i dati del messaggio dell'utente
    if not context.args:
        await update.effective_message.reply_text(
            "⚠️ Devi specificare il nome della mensa.\n"
            "Esempio: /unsubscribe_canteen [NOME_MENSA]"
        )
        return
    
    # The user write correctly the command 
    canteen_name = " ".join(context.args) if context.args else ""
    canteen = await canteen_repo.get_by_name(canteen_name)
    
    if not canteen or canteen.id is None:
        all_canteens = await canteen_repo.get_all_active()
        msg = (
            f"<b>❌ Mensa '{canteen_name}' non trovata nel database.</b>\n\n"
            "<i>Devi inserire una di queste mense:</i>\n\n"
        )
        for c in all_canteens:
            msg += f"📍 <b>{c.name}</b>\n   <i>{c.location_description}</i>\n\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
        return
    
    canteen_id: int = canteen.id
    
    success = await user_repo.remove_canteen_from_user(telegram_id, canteen_id)
    
    if success:
        user_canteen_ids = await user_repo.get_user_canteens(telegram_id)
        
        msg = f"✅ Disiscritto correttamente da <b>{canteen.name}</b>.\n\n"
        
        if user_canteen_ids:
            msg += f"📋 <b>Sei ancora iscritto a {len(user_canteen_ids)} mensa/e:</b>\n"
            for cid in user_canteen_ids:
                c = await canteen_repo.get_by_id(cid)
                if c:
                    msg += f"  • {c.name}\n"
        else:
            msg += "ℹ️ Non sei più iscritto a nessuna mensa."
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
    else:
        await update.effective_message.reply_text(
            f"⚠️ Non eri iscritto alla mensa <b>{canteen.name}</b>.",
            parse_mode='HTML'
        )
            
"""
    ADMIN ONLY
"""
@inject_db
async def add_mensa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    
    """
        Funzione per un admin per aggiungere una nuova mensa (VA TROVATO UN NUOVO NOME)
    """
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the add_mensa command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /add_mensa command received from {telegram_id}")
    
    if telegram_id not in ADMIN_IDS:
        logger.error("Messaggio /add_mensa non inviato da un admin")
        if update.effective_message:
            await update.effective_message.reply_text(
                "Non hai i permessi per eseguire questo comando."
            )
        return
    
    if not context.args:
        logger.error("Argomenti mancanti nel comando /add_mensa")
        if update.effective_message:
            await update.effective_message.reply_text(
                "Hai digitato male il messaggio /add_mensa [NOME_MENSA] [INDIRIZZO]"
            )
        return
    if len(context.args) < 2:
        logger.error("Via mancante nel comando /add_mensa")
        if update.effective_message:
            await update.effective_message.reply_text(
                "Hai digitato male il messaggio /add_mensa [NOME_MENSA] [INDIRIZZO]"
            )
        return
    
    canteen_repository = CanteenRepository(session)
    
    all_canteen = await canteen_repository.get_all_active()
    
    new_canteen = Canteen(
        name=context.args[0], location_description=context.args[1]
    )
    
    if new_canteen in all_canteen:
        await update.effective_message.reply_text("Mensa già esistente")
        return
    
    await canteen_repository.create(new_canteen)
    
    if update.effective_message:
        await update.effective_message.reply_text(
            f"Mensa {context.args[0]} situata in {context.args[1]} aggiunta correttamente"
        )

"""
    ADMIN ONLY
"""
@inject_db
async def delete_mensa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    
    """
        Funzione per un admin per aggiungere una nuova mensa (VA TROVATO UN NUOVO NOME)
    """
    if not update.effective_user:
        return
    
    if session is None:
        logger.error("Session is None in the add_mensa command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /delete_mensa command received from {telegram_id}")
    
    if telegram_id not in ADMIN_IDS:
        logger.error("Messaggio /delete_mensa non inviato da un admin")
        if update.effective_message:
            await update.effective_message.reply_text(
                "Non hai i permessi per eseguire questo comando."
            )
        return
    
    if not context.args:
        logger.error("Argomenti mancanti nel comando /delete_mensa")
        if update.effective_message:
            await update.effective_message.reply_text(
                "Hai digitato male il messaggio /delete_mensa [NOME_MENSA]"
            )
        return
    
    canteen_repo = CanteenRepository(session)   
    canteen_name = context.args[0]
    canteen = await canteen_repo.get_by_name(canteen_name)
    all_canteens = await canteen_repo.get_all_active()
    
    if not canteen:
        if update.effective_message:
            msg = await update.effective_message.reply_text(
                 f"❌ Mensa '{canteen_name}' non trovata nel database.\nDevi inserire una di queste mense:"
            )
            # we need to store previous message text in order to add new content
            # otherwise edit_text will reset the message
            text = msg.text if msg.text != None else ""
            for canteen in all_canteens:
                text += f"\n{canteen.name}\n"
            await msg.edit_text(f"{text}")
        return 
    
    if canteen.id is None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Errore: la mensa non ha un ID valido."
            )
        return

    success = await canteen_repo.delete(canteen.id)
    
    if success:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Mensa cancellata correttamente."
            )
    else:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Si è verificato un problema durante la cancellazione della mensa"
            )


@inject_db
async def print_all_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    
    """
        Funzione per un admin per aggiungere una nuova mensa (VA TROVATO UN NUOVO NOME)
    """
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the add_mensa command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /print_all_canteen command received from {telegram_id}")
    
    canteen_repo = CanteenRepository(session)
    all_canteens = await canteen_repo.get_all_active()
    if not all_canteens:
       await update.effective_message.reply_text(
            "Nessuna mensa configurata nel database",
        )
       return
    msg = "Ecco a te una lista di tutte le mense disponibili: \n\n"
    for cantine in all_canteens:
        msg += f"<b>{cantine.name}</b>\nÈ attiva? {'✅' if cantine.is_active else '❌'}\n📍:{cantine.location_description}\n\n"
        
    await update.effective_message.reply_text(
        msg,
        parse_mode='HTML'
    )


@inject_db
async def print_subscribed_canteen(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    
    """
        Funzione per un admin per aggiungere una nuova mensa (VA TROVATO UN NUOVO NOME)
    """
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the print_subscribed_canteen command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /print_all_canteen command received from {telegram_id}")
    
    user_repo = UserRepository(session)
    canteen_repo = CanteenRepository(session)
    all_canteens = await canteen_repo.get_all_active()
    user = await user_repo.get_by_telegram_id(telegram_id)

    if not user:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Non sei registrato. Usa /start prima."
            )
        return
    
    if not user.selected_canteen_ids:
        await update.effective_message.reply_text(
            "Non sei iscritto a nessuna mensa, iscriviti a una mensa con /subscribe_canteen [NOME_MENSA]",
        )
        return
   
    if not all_canteens:
       await update.effective_message.reply_text(
            "Nessuna mensa configurata nel database",
        )
       return
    msg = "Ecco a te una lista di tutte le mense a cui sei iscritto: \n\n"
    
    
    for cantine in all_canteens:
        if cantine.id in user.selected_canteen_ids:
            msg += f"<b>{cantine.name}</b>\nÈ attiva? {'✅' if cantine.is_active else '❌'}\n📍:{cantine.location_description}\n\n"
        
    await update.effective_message.reply_text(
        msg,
        parse_mode='HTML'
    )

@inject_db
async def set_language(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    if not update.effective_user or not update.effective_message:
        return None
    
    if session is None:
        logger.error("Session is None in set_language command")
        return
        
    telegram_id = update.effective_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if user is None:
        await update.effective_message.reply_text(
            "Utente non trovato nel database"
        )
        return
    
    if context.args is None:
        await update.effective_message.reply_text(
            "Sintassi incorretta. Per impostare la lingua usa il comando /set_language [LINGUA]"
        )
        return
    if len(context.args) < 1:
        await update.effective_message.reply_text(
            "Sintassi incorretta. Per impostare la lingua usa il comando /set_language [LINGUA]"
        )
        return
    
    if context.args[0].lower() not in LINGUE_SUPPORTATE:
        msg =  "Lingua non supportata dall'attuale versione del bot.\nLe lingue supportate sono:\n"
        for language in LINGUE_SUPPORTATE:
            msg += f"- {language}\n"
        await update.effective_message.reply_text(
           msg
        )
        return
    language = context.args[0]
    success = await user_repo.update_user_language(telegram_id, language)
    
    if success:
        await update.effective_message.reply_text(f"Lingua impostata correttamente a {language}")
    else:
        await update.effective_message.reply_text("Utente non trovato")


async def get_current_language(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    if not update.effective_user or not update.effective_message:
        return None
    
    if session is None:
        logger.error("Session is None in set_language command")
        return
        
    telegram_id = update.effective_user.id
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    
    if user is None:
        await update.effective_message.reply_text(
            "Utente non trovato nel database"
        )
        return
    return user.language
    