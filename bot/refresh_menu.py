import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from database.repositories import UserRepository
from services.scraper_service import fetch_and_store_menus
from utils.decorator import inject_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

@inject_db
async def refresh_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    if not session or not update.effective_user or not update.effective_message:
        return
    
    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text("❌ Comando riservato agli admin.")
        return

    status_msg = await update.effective_message.reply_text(
        "🔄 Avvio aggiornamento menu...\nQuesta operazione potrebbe richiedere qualche minuto."
    )
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