import os
from dotenv import load_dotenv
# Import env variabile 
load_dotenv()
IG_USERNAME = os.getenv('IG_USERNAME')
IG_PASSWORD = os.getenv('IG_PASSWORD')
TARGET_USER = os.getenv('TARGET_USER')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SESSION_FILE = os.getenv('SESSION_FILE')
SUBSCRIBERS_FILE = os.getenv('SUBSCRIBERS_FILE')
DOWNLOAD_DIR = "stories"
MAX_RETRIES = 3