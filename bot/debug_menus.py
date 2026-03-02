
from sqlmodel import select
from telegram import Update
from telegram.ext import ContextTypes

from database.models import Menu
from database.repositories import CanteenRepository, UserRepository
from utils.decorator import inject_db
from utils.logger import setup_logger
from utils.today import get_today_date

logger = setup_logger(__name__)

@inject_db
async def debug_menus(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None):
    """Debug: mostra tutti i menu nel DB"""
    if not session or not update.effective_message or not update.effective_user:
        return

    user_repo = UserRepository(session)
    if not await user_repo.is_admin(update.effective_user.id):
        await update.effective_message.reply_text(
            "❌ Comando riservato agli admin."
        )
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
    