
from functools import wraps
from typing import Any, Callable

from telegram import Update
from telegram.ext import ContextTypes

from database.connection import get_session_maker
from utils.logger import setup_logger


logger = setup_logger(__name__)


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
