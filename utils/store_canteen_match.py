from database.models import Canteen
from utils.get_canteen_keywords import get_canteen_keywords


def store_canteen_match(text: str, canteen: Canteen):
    keywords = get_canteen_keywords(canteen)
    score = 0
    for kw in keywords:
        if kw in text:
            score += 1
    return score
    
    