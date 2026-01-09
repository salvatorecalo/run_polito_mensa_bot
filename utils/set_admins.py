from database.connection import get_session_maker
from database.repositories import UserRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def set_admins(telegram_ids):
    """
    Imposta utenti come admin. 
    Se l'utente non esiste, lo crea con nome placeholder.
    
    Args:
        telegram_ids: Lista di Telegram ID (stringhe o interi)
    """
    Session = get_session_maker()
    session = Session()
    try:
        user_repo = UserRepository(session)
        
        for tid in telegram_ids:
            # Converti in int se è stringa
            tid_int = int(tid) if isinstance(tid, str) else tid
            
            # Cerca l'utente
            user = await user_repo.get_by_telegram_id(tid_int)
            
            if user:
                # Utente esiste, impostalo come admin
                if not user.is_admin:
                    user.is_admin = True
                    logger.info(f"✅ Utente {user.first_name} ({tid_int}) impostato come admin")
                else:
                    logger.info(f"ℹ️  Utente {user.first_name} ({tid_int}) è già admin")
            else:
                # Utente non esiste, crealo come admin
                logger.warning(f"⚠️  Utente {tid_int} non trovato, lo creo come admin placeholder")
                user = await user_repo.get_or_create(
                    telegram_id=tid_int,
                    first_name="Admin",  # Verrà aggiornato al primo /start
                    username=None
                )
                user.is_admin = True
                logger.info(f"✅ Utente admin {tid_int} creato (userà /start per aggiornare il profilo)")
        
        await session.commit()
        logger.info(f"✅ Configurazione admin completata per {len(telegram_ids)} utenti")
        
    except Exception as e:
        await session.rollback()
        logger.error(f"❌ Errore durante set_admins: {e}", exc_info=True)
        raise
    finally:
        await session.close()