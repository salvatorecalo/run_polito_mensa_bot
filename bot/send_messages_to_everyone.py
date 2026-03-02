import asyncio
from asyncio.log import logger
from telegram import Update
from telegram.ext import ContextTypes
from database.repositories import UserRepository
from services.telegram_service import TelegramService
from utils.decorator import inject_db
from utils.logger import setup_logger

logger = setup_logger(__name__)

@inject_db
async def send_message_to_everyone(update: Update, context: ContextTypes.DEFAULT_TYPE, session=None) -> None:
    if not session:
        return
    
    if not update or not update.effective_message or not update.effective_user:
        return
        
    if not context.args:
        await update.effective_message.reply_text("⚠️ Usa: /broadcast <messaggio>")
        return
        
    broadcast_msg = " ".join(context.args)
    user_id = update.effective_user.id
    
    telegram_service = TelegramService()
    user_repo = UserRepository(session)
            
    if not await user_repo.is_admin(user_id):
        await update.effective_message.reply_text("❌ Non hai i permessi per questa azione.")
        return
            
    logger.info(f"📢 Avvio broadcast da parte di {user_id}")
    
    all_users = await user_repo.get_all()
    count = 0
    
    for user in all_users:
        if user.telegram_id == update.effective_user.id:
            continue
        try:
            await telegram_service.send_message(
                chat_id=user.telegram_id, 
                text=broadcast_msg
            )
            count += 1
            # Anti-flood (limite Telegram 30 msg/s)
            await asyncio.sleep(0.05) 
        except Exception as e:
            logger.error(f"Errore invio a {user.telegram_id}: {e}")
    await update.effective_message.reply_text(f"✅ Broadcast completato. Inviata a {count} utenti.")