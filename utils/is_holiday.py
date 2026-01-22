from .today import get_today_date
from datetime import date, timedelta

def is_holiday() -> bool:
    today = get_today_date()
    year = today.year
    # FORMAT YEAR/MONTH/DAY
    if date(year, 7, 25) <= today <= date(year, 9, 15):
        return True  # Summer break
    
    if today >= date(year, 12, 20) or today <= date(year, 1, 7):
        return True # Christmas break

    fixed_holidays = [
        (4, 25),  # Liberazione
        (5, 1),   # Festa del Lavoro
        (6, 2),   # Festa della Repubblica
        (6, 24),  # San Giovanni (Patrono Torino - Fondamentale per EDISU!)
        (11, 1),  # Ognissanti
        (12, 8),  # Immacolata
    ]
    if (today.month, today.day) in fixed_holidays:
        return True

    # Easter Holiday (Butcher alghorithm)
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    
    easter = date(year, month, day)
    easter_monday = easter + timedelta(days=1)
    
    if today == easter or today == easter_monday:
        return True # Easter
    return False