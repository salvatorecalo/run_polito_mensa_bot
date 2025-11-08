"""
Costanti dell'applicazione
"""

# Dimensioni immagini
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
MIN_FONT_SIZE = 40
MAX_FONT_SIZE = 80
IMAGE_MARGIN = 60  # Margine dai bordi

# Colori (RGB)
BG_COLOR = (255, 140, 0)  # Arancione
TEXT_COLOR = (255, 255, 255)  # Bianco

# Telegram
TELEGRAM_BATCH_SIZE = 10  # Limite Telegram per media group

# Timing
RETRY_DELAY = 2  # secondi

# Schedulazione (orari invio menu)
SCHEDULE_TIMES = [
    {"hour": 11, "minute": 25},  # Pranzo
    {"hour": 20, "minute": 0}     # Cena
]