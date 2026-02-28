import os
from pathlib import Path
from .logger import setup_logger

logger = setup_logger(__name__)

def setup_data_folder():
    try:
        os.makedirs("data", exist_ok=True)
        os.makedirs("download", exist_ok=True)
        os.makedirs("download/stories", exist_ok=True)
        os.makedirs("download/created_images", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        Path("data/bot.db").touch()
        logger.info("Cartelle data and download create con successo")
    except Exception as e:
        logger.error(e)
    

    