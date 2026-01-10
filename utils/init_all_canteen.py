from database.connection import get_session_maker
from database.models import Canteen
from database.repositories import CanteenRepository
from utils.read_canteens_from_file import read_canteens_from_file
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def init_all_canteen():
    session_maker = get_session_maker()
    if not session_maker:
        logger.error("❌ Session maker non inizializzato")
    
    session = session_maker()
    canteen_repo = CanteenRepository(session)
    try:
        canteens = read_canteens_from_file()
        for canteen in canteens:
            existing = await canteen_repo.get_by_name(canteen["name"])
            if existing:
                logger.info(f"ℹ️ Mensa già presente: {canteen['name']}")
                continue
            new_canteen = Canteen(
                name=canteen["name"],
                location_description=canteen["location"],
                is_active=True
            )
            
            await canteen_repo.create(new_canteen)
            logger.info(f"✅ Mensa inserita: {canteen['name']}")
        await session.commit()
    except Exception as e:
        logger.error(f"❌ Errore init mense: {e}", exc_info=True)
        await session.rollback()

    finally:
        await session.close()
        logger.info("🔒 Sessione DB chiusa")
