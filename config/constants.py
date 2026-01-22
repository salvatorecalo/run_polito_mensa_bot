"""
Costanti dell'applicazione
"""

# Image dimension
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
MIN_FONT_SIZE = 40
MAX_FONT_SIZE = 80
IMAGE_MARGIN = 60  # Border margin

# Colors (RGB)
BG_COLOR = (255, 140, 0)  # Orange
TEXT_COLOR = (255, 255, 255)  # White

# Telegram
TELEGRAM_BATCH_SIZE = 10  # Telegram limit for media group

# Scheduling (times for menu to be sent)
SCHEDULE_TIMES = [
    {"hour": 11, "minute": 25},  # Lunch
    {"hour": 20, "minute": 0}     # Dinner
]
