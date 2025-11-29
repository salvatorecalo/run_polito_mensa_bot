"""
Telegram Bot Handlers with Dependency Injection and Async Database Support
"""

import logging
from datetime import date, datetime
from functools import wraps
from typing import Any, Callable

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database.connection import get_session
from database.repositories import CanteenRepository, MenuRepository, UserRepository
from database.models import Canteen

from config.constants import ADMIN_IDS

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
        # Get a new session from the generator
        async for session in get_session():
            try:
                # Pass the session as a keyword argument to the handler
                return await func(update, context, session=session, *args, **kwargs)
            except Exception as e:
                logger.error(
                    f"❌ Database error in handler {func.__name__}: {e}", exc_info=True
                )
                if update.effective_message:
                    await update.effective_message.reply_text(
                        "⚠️ Si è verificato un errore interno. Riprova più tardi."
                    )
            # Session closes automatically here due to context manager in get_session

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
            if update.effective_message:
                await update.effective_message.reply_text(
                    f"👋 Ciao {user.first_name}! Ti sei iscritto con successo.\n\n"
                    "Riceverai i menu delle mense che configuri ogni giorno.\n"
                    "Usa /menu per vedere il menu di oggi.\n"
                    "Usa /cancel per disiscriverti.\n"
                    "Usa /subscribe_canteen [NOME_MENSA] per ricevere i menù di quella mensa.\n"
                    "Usa /unsubscribe_canteen [NOME_MENSA] per smettere di ricevere i menù di quella mensa.\n"
                    "Puoi ricevere contemporaneamente il menù di più mense \n"
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
    if not update.effective_user:
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
    canteen_id = user.selected_canteen_id

    if not canteen_id:
        # Fallback: Try to find a default canteen or ask user
        # For now, let's try to get the first active canteen
        canteens = await canteen_repo.get_all_active()
        if canteens:
            canteen_id = canteens[0].id
            # Auto-set preference for convenience
            if canteen_id is not None:
                await user_repo.update_canteen_preference(telegram_id, canteen_id)
        else:
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Nessuna mensa configurata nel sistema."
                )
            return

    # 2. Fetch Menu
    today = date.today()

    # Determine meal type based on time (Lunch < 15:00 <= Dinner)
    # Simple logic: if it's morning/early afternoon show lunch, else dinner
    current_hour = datetime.now().hour
    meal_type = "lunch" if current_hour < 15 else "dinner"

    # Safety check: canteen_id should not be None at this point
    if canteen_id is None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Errore di configurazione mensa."
            )
        return

    menu = await menu_repo.get_menu_by_date(today, canteen_id, meal_type)

    # 3. Respond
    if not menu:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"📅 *Menu del {today.strftime('%d/%m/%Y')} ({meal_type})*\n\n"
                "❌ Il menu non è ancora disponibile nel database.\n"
                "Riprova più tardi, il bot controlla automaticamente le nuove storie.",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    # Format the response
    canteen = await canteen_repo.get_by_id(canteen_id) if canteen_id else None
    canteen_name = canteen.name if canteen else "Mensa"
    response_text = f"🍽️ *Menu {canteen_name}*\n📅 {menu.date}\n\n"

    if menu.translated_text:
        # If we have the full translated text block
        response_text += menu.translated_text
    else:
        # Fallback to JSON parsing
        courses = menu.courses_json
        if isinstance(courses, dict):
            for course_type, dishes in courses.items():
                response_text += f"*{course_type.upper()}*:\n"
                for dish in dishes:
                    response_text += f"- {dish}\n"
                response_text += "\n"

    if update.effective_message:
        await update.effective_message.reply_text(
            response_text, parse_mode=ParseMode.MARKDOWN
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
    
    if not update.effective_user:
        return

    if session is None:
        logger.error("Session is None in add_canteen command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /add_canteen command received from {telegram_id}")

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
                "Esempio: /add_canteen Nome Mensa"
            )
        return
    
    # The user write correctly the command 
    canteen_name = " ".join(context.args) if context.args else ""
    
    canteen = await canteen_repo.get_by_name(canteen_name)
    all_canteens = await canteen_repo.get_all_active()
    if not canteen:
        if update.effective_message:
            msg = await update.effective_message.reply_text(
                 f"❌ Mensa '{canteen_name}' non trovata nel database.\nDevi inserire una di queste mense:"
            )
            # we need to store previous message text in order to add new content
            # otherwise edit_text will reset the message
            text = msg.text
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
    
    canteen_id: int = canteen.id
    
    if user.id in [u.id for u in await user_repo.get_users_by_canteen(canteen_id)]:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"Sei già iscritto in {canteen.name}\n Per disicriverti usa /unsubscribe_canteen"
            )
        return
    
    success = await user_repo.update_canteen_preference(telegram_id, canteen.id)
    
    if success:
        if update.effective_message:
            await update.effective_message.reply_text(
                f"✅ Mensa '{canteen_name}' aggiunta con successo!\n"
                "Riceverai i menu di questa mensa."
            )
    else:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Errore nell'aggiunta della mensa. Riprova più tardi."
            )

@inject_db
async def add_mensa(
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
    logger.info(f"🍽️ /add_mensa command received from {telegram_id}")
    
    if telegram_id not in ADMIN_IDS:
        logger.error("Messaggio /add_mensa non inviato da un admin")
        if update.effective_message:
            update.effective_message.reply_text(
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
    elif not context.args[1]:
        logger.error("Via mancante nel comando /add_mensa")
        if update.effective_message:
            await update.effective_message.reply_text(
                "Hai digitato male il messaggio /add_mensa [NOME_MENSA] [INDIRIZZO]"
            )
        return
    
    canteen_repository = CanteenRepository(session)
    new_canteen = Canteen(
        name=context.args[0], location_description=context.args[1]
    )
    
    await canteen_repository.create(new_canteen)
    
    if update.effective_message:
        await update.effective_message.reply_text(
            f"Mensa {context.args[0]} situata in {context.args[1]} aggiunta correttamente"
        )


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
            update.effective_message.reply_text(
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
            text = msg.text
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

            
    
    