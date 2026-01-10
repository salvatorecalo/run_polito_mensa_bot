from typing import List
from database.models import Canteen
from utils.logger import setup_logger

logger = setup_logger(__name__)

def write_canteens_to_file(canteens: List[Canteen]) -> None:
    try:
        infile = open("data/canteens.csv", "w")
        for canteen in canteens:
            infile.write(f"{canteen.name},{canteen.location_description},{canteen.is_active}")
    except Exception as e:
       logger.error(f"❌ Si è generata un eccezione {e}")
    finally:
        infile.close()