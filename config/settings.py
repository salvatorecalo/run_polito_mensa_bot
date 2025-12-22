import os
from pathlib import Path
from dotenv import load_dotenv
from utils.convert_admin_ids import convert_admin_ids

# Determina il percorso della root del progetto
ROOT_DIR = Path(__file__).parent.parent
ENV_FILE = ROOT_DIR / '.env'

# Carica variabili d'ambiente (override=True per sovrascrivere eventuali variabili già esistenti)
load_dotenv(dotenv_path=ENV_FILE, override=True)

# Instagram
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')
TARGET_USER = os.getenv('TARGET_USER')
SESSION_FILE = os.getenv('SESSION_FILE', 'data/ig_session.json')

# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SUBSCRIBERS_FILE = os.getenv('SUBSCRIBERS_FILE', 'data/subscribers.json')

DOWNLOAD_DIR = "download/stories"
CREATED_IMAGES_DIR = "download/created_images"

# Retry
MAX_RETRIES = 3

ADMIN_IDS = convert_admin_ids(os.getenv('TELEGRAM_BOT_ADMINS', ""))
