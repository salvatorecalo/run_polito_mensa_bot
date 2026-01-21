from zoneinfo import ZoneInfo
from datetime import datetime, date

def get_today_date() -> date:
    return datetime.now(ZoneInfo("Europe/Rome")).date()

# For backward compatibility, but deprecated
TODAY_DATE: date = get_today_date()