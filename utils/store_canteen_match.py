from database.models import Canteen
from utils.get_canteen_keywords import get_canteen_keywords
from utils import normalize_text

def store_canteen_match(text: str, canteen: Canteen):
    text_norm = normalize_text(text)
    name_norm = normalize_text(canteen.name)
    
    # If the exact canteen name is in the text, give high score
    if name_norm in text_norm:
        return 10
    
    # Fallback to keyword matching
    keywords = get_canteen_keywords(canteen)
    score = 0
    for kw in keywords:
        if kw in text_norm:
            score += 1
    return score
    
    