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
from utils.my_translation import get_text

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
            await session.rollback()
            
            if update.effective_message:
                await update.effective_message.reply_text(
                    "⚠️ Si è verificato un errore interno. Riprova più tardi."
                )
        finally:
            await session.close()

    return wrapper


# --- Helper Functions ---

async def get_user_language(session, telegram_id: int) -> str:
    """Get user's language preference, default to italiano"""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    return user.language if user else "italiano"


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
            await update.effective_message.reply_text(
                get_text(language, "welcome_back")
            )
        else:
            await update.effective_message.reply_text(
                get_text(language, "welcome_new", name=user.first_name)
            )

    except Exception as e:
        raise e


@inject_db
async def menu_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
) -> None:
    """Handler for /menu. Fetches today's menu from the DB."""
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
        await update.effective_message.reply_text(
            get_text("italiano", "not_registered")
        )
        return

    language = user.language
    canteen_ids = user.selected_canteen_ids

    if not canteen_ids:
        await update.effective_message.reply_text(
            get_text(language, "no_canteens_subscribed"),
            parse_mode='HTML'
        )
        return

    today = date.today()
    current_hour = datetime.now().hour
    meal_type = "lunch" if current_hour < 15 else "dinner"
    meal_type_translated = get_text(language, meal_type)

    menus = await menu_repo.get_menus_by_date_for_canteens(
        today, canteen_ids, meal_type
    )

    if not menus:
        await update.effective_message.reply_text(
            get_text(language, "no_menu_available", 
                    date=today.strftime('%d/%m/%Y'), 
                    meal_type=meal_type_translated),
            parse_mode='HTML'
        )
        return

    response_text = get_text(language, "menu_title", 
                            date=today.strftime('%d/%m/%Y'), 
                            meal_type=meal_type_translated)
    
    for menu in menus:
        canteen = await canteen_repo.get_by_id(menu.canteen_id)
        if not canteen:
            continue
        
        response_text += f"📍 <b>{canteen.name}</b>\n"
        response_text += f"   <i>{canteen.location_description}</i>\n\n"
        
        # Use appropriate text based on language
        if language == "english" and menu.translated_text:
            response_text += menu.translated_text + "\n\n"
        elif language == "italiano" and menu.original_text:
            response_text += menu.original_text + "\n\n"
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
    """Handler for /cancel. Deactivates the user."""
    if not update.effective_user or not update.effective_message:
        return

    if session is None:
        logger.error("Session is None in cancel_command")
        return

    telegram_id = update.effective_user.id
    repo = UserRepository(session)

    language = await get_user_language(session, telegram_id)
    success = await repo.update_status(telegram_id, is_active=False)

    if success:
        await update.effective_message.reply_text(
            get_text(language, "cancel_success")
        )
    else:
        await update.effective_message.reply_text(
            get_text(language, "not_subscribed_service")
        )


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
        await update.effective_message.reply_text(
            get_text("italiano", "not_registered")
        )
        return
    
    language = user.language
    
    if not context.args:
        await update.effective_message.reply_text(
            get_text(language, "specify_canteen_name")
        )
        return
    
    canteen_name = " ".join(context.args)
    canteen = await canteen_repo.get_by_name(canteen_name)
    
    if not canteen or canteen.id is None:
        all_canteens = await canteen_repo.get_all_active()
        msg = get_text(language, "canteen_not_found", name=canteen_name) + "\n\n"
        
        for c in all_canteens:
            msg += f"📍 <b>{c.name}</b>\n   <i>{c.location_description}</i>\n\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
        return 
    
    canteen_id: int = canteen.id
    success = await user_repo.add_canteen_to_user(telegram_id, canteen_id)
    
    if success:
        user_canteen_ids = await user_repo.get_user_canteens(telegram_id)
        
        msg = get_text(language, "subscribe_success", 
                      name=canteen.name, 
                      count=len(user_canteen_ids))
        
        for cid in user_canteen_ids:
            c = await canteen_repo.get_by_id(cid)
            if c:
                msg += f"  • {c.name}\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
    else:
        await update.effective_message.reply_text(
            get_text(language, "already_subscribed", name=canteen.name),
            parse_mode='HTML'
        )


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
        await update.effective_message.reply_text(
            get_text("italiano", "not_registered")
        )
        return
    
    language = user.language
    
    if not context.args:
        await update.effective_message.reply_text(
            get_text(language, "specify_canteen_name")
        )
        return
    
    canteen_name = " ".join(context.args)
    canteen = await canteen_repo.get_by_name(canteen_name)
    
    if not canteen or canteen.id is None:
        all_canteens = await canteen_repo.get_all_active()
        msg = get_text(language, "canteen_not_found", name=canteen_name) + "\n\n"
        
        for c in all_canteens:
            msg += f"📍 <b>{c.name}</b>\n   <i>{c.location_description}</i>\n\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
        return
    
    canteen_id: int = canteen.id
    success = await user_repo.remove_canteen_from_user(telegram_id, canteen_id)
    
    if success:
        user_canteen_ids = await user_repo.get_user_canteens(telegram_id)
        
        msg = get_text(language, "unsubscribe_success", name=canteen.name)
        
        if user_canteen_ids:
            msg += get_text(language, "still_subscribed_to", count=len(user_canteen_ids))
            for cid in user_canteen_ids:
                c = await canteen_repo.get_by_id(cid)
                if c:
                    msg += f"  • {c.name}\n"
        else:
            msg += get_text(language, "no_more_subscriptions")
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
    else:
        await update.effective_message.reply_text(
            get_text(language, "not_subscribed", name=canteen.name),
            parse_mode='HTML'
        )


# --- ADMIN COMMANDS ---

@inject_db
async def add_mensa(
    update: Update, context: ContextTypes.DEFAULT_TYPE, session=None
):
    """Admin command to add a new canteen"""
    if not update.effective_user or not update.effective_message:
        return
    
    if session is None:
        logger.error("Session is None in the add_mensa command")
        return
    
    telegram_id = update.effective_user.id
    logger.info(f"🍽️ /add_mensa command received from {telegram_id}")
    
    language = await get_user_language(session, telegram_id)
    
    if telegram_id not in ADMIN_IDS:
        logger.error("Messaggio /add_mensa non inviato da un admin")
        await update.effective_message.reply_text(
            get_text(language, "no_permission")
        )
        return
    
    if not context.args or len(context.args) < 2:
        logger.error("Argomenti mancanti nel comando /add_mensa")
        await update.effective_message.reply_text(
            get_text(language, "add_mensa_syntax")
        )
        return
    
    canteen_repository = CanteenRepository(session)
    
    new_canteen = Canteen(
        name=context.args[0], 
        location_description=" ".join(context.args[1:])
    )
    
    # Check if already exists
    existing = await canteen_repository.get_by_name(new_canteen.name)
    if existing:
        await update.effective_message.reply_text(
            get_text(language, "canteen_already_exists")
        )
        return
    
    await canteen_repository.create(new_canteen)
    
    await update.effective_message.reply_text(
        get_text(language, "canteen_added_success", 
                name=new_canteen.name, 
                location=new_canteen.location_description)
    )


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
    
    language = await get_user_language(session, telegram_id)
    
    if telegram_id not in ADMIN_IDS:
        logger.error("Messaggio /delete_mensa non inviato da un admin")
        await update.effective_message.reply_text(
            get_text(language, "no_permission")
        )
        return
    
    if not context.args:
        logger.error("Argomenti mancanti nel comando /delete_mensa")
        await update.effective_message.reply_text(
            get_text(language, "delete_mensa_syntax")
        )
        return
    
    canteen_repo = CanteenRepository(session)   
    canteen_name = " ".join(context.args)
    canteen = await canteen_repo.get_by_name(canteen_name)
    
    if not canteen or canteen.id is None:
        all_canteens = await canteen_repo.get_all_active()
        msg = get_text(language, "canteen_not_found", name=canteen_name) + "\n\n"
        
        for c in all_canteens:
            msg += f"  • {c.name}\n"
        
        await update.effective_message.reply_text(msg, parse_mode='HTML')
        return 

    success = await canteen_repo.delete(canteen.id)
    
    if success:
        await update.effective_message.reply_text(
            get_text(language, "canteen_deleted_success", name=canteen.name)
        )
    else:
        await update.effective_message.reply_text(
            get_text(language, "canteen_delete_error")
        )


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
    
    language = await get_user_language(session, telegram_id)
    canteen_repo = CanteenRepository(session)
    all_canteens = await canteen_repo.get_all_active()
    
    if not all_canteens:
        await update.effective_message.reply_text(
            get_text(language, "no_canteens_in_db")
        )
        return
    
    msg = get_text(language, "all_canteens_list") + "\n\n"
    
    for canteen in all_canteens:
        msg += f"📍 <b>{canteen.name}</b>\n"
        msg += f"   <i>{canteen.location_description}</i>\n"
        msg += f"   {'✅' if canteen.is_active else '❌'}\n\n"
        
    await update.effective_message.reply_text(msg, parse_mode='HTML')


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
        await update.effective_message.reply_text(
            get_text("italiano", "not_registered")
        )
        return
    
    language = user.language
    
    if not user.selected_canteen_ids:
        await update.effective_message.reply_text(
            get_text(language, "no_canteens_subscribed")
        )
        return
    
    msg = get_text(language, "subscribed_canteens_list") + "\n\n"
    
    for canteen_id in user.selected_canteen_ids:
        canteen = await canteen_repo.get_by_id(canteen_id)
        if canteen:
            msg += f"📍 <b>{canteen.name}</b>\n"
            msg += f"   <i>{canteen.location_description}</i>\n"
            msg += f"   {'✅' if canteen.is_active else '❌'}\n\n"
        
    await update.effective_message.reply_text(msg, parse_mode='HTML')


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
        await update.effective_message.reply_text(
            get_text(current_language, "set_language_syntax")
        )
        return
    
    language = context.args[0].lower()
    
    if language not in LINGUE_SUPPORTATE:
        msg = get_text(current_language, "language_not_supported")
        for lang in LINGUE_SUPPORTATE:
            msg += f"  • {lang}\n"
        await update.effective_message.reply_text(msg)
        return
    
    success = await user_repo.update_user_language(telegram_id, language)
    
    if success:
        await update.effective_message.reply_text(
            get_text(language, "language_set")
        )
    else:
        await update.effective_message.reply_text(
            "Error / Errore"
        )