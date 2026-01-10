from typing import List
from bot.handlers import inject_db
from database.models import Canteen
from database.repositories import CanteenRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)

CANTEENS_FILE_NAME = "../data/canteens.csv"

async def read_canteens_from_file(session= None) -> None:
    if not session:
        logger.error("Nessuna sessione trovata in read_canteens_from_file")
        return
    canteen_repo = CanteenRepository(session)
    try:
        infile = open("data/canteens.csv", "r")
        for line in infile:
            campi = line.split(",")
            existing = await canteen_repo.get_by_name(campi[0])
            if existing:
                logger.info(f"Mensa {campi[0]} già esistente, saltata")
                continue
            new_canteen = Canteen(
                name=campi[0],
                location_description=campi[1],
                is_active=bool(campi[2])
            )
            session.add(new_canteen)
        await session.commit()
    except FileNotFoundError:
        logger.error("❌ File data/canteens.csv non trovato")
    except Exception as e:
        logger.error(f"❌ Exception while reading canteens.csv {e}")
    finally:
        infile.close()