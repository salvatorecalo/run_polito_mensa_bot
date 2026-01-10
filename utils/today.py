from zoneinfo import ZoneInfo
from datetime import datetime, date

TODAY_DATE: date = datetime.now(ZoneInfo("Europe/Rome")).date()