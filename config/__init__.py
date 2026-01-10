"""
Package di configurazione del bot
"""
from .settings import *
from .constants import *

__all__ = [
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID',
    'DOWNLOAD_DIR',
    'CREATED_IMAGES_DIR',
    'MAX_RETRIES',
    'IMAGE_WIDTH',
    'IMAGE_HEIGHT',
    'MIN_FONT_SIZE',
    'MAX_FONT_SIZE',
    'IMAGE_MARGIN',
    'BG_COLOR',
    'TEXT_COLOR',
    'TELEGRAM_BATCH_SIZE',
    'SCHEDULE_TIMES',
]