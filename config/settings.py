import os
from pathlib import Path
from dotenv import load_dotenv

# Determina il percorso della root del progetto
ROOT_DIR = Path(__file__).parent.parent
ENV_FILE = ROOT_DIR / '.env'

# Carica variabili d'ambiente (override=True per sovrascrivere eventuali variabili già esistenti)
load_dotenv(dotenv_path=ENV_FILE, override=True)

# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

DOWNLOAD_DIR = "download/stories"
CREATED_IMAGES_DIR = "download/created_images"

GROQ_API_KEY=os.getenv("GROQ_API_KEY")
# Retry
MAX_RETRIES = 3

