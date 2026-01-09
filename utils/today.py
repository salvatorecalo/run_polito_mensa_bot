from zoneinfo import ZoneInfo
from datetime import datetime

today = datetime.now(ZoneInfo("Europe/Rome")).date()