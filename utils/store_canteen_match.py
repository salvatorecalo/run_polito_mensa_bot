from database.models import Canteen
from utils.get_canteen_keywords import get_canteen_keywords
from utils import normalize_text

def store_canteen_match(text: str, canteen: Canteen):
    text_norm = normalize_text(text)
    name_norm = normalize_text(canteen.name)
    
    # --- LIVELLO 1: IL NOME SPECIFICO (Il più forte) ---
    # Prendiamo solo l'ultima parola del nome (es: Borsellino, Olimpia, Castelfidardo)
    # Evitiamo "Mensa" e "Universitaria"
    specific_name = name_norm.split()[-1] 
    if len(specific_name) > 3 and specific_name in text_norm:
        return 15

    # --- LIVELLO 2: NOME COMPLETO SENZA SPAZI (Per Castelfidardo) ---
    text_no_spaces = text_norm.replace(" ", "")
    name_no_spaces = name_norm.replace(" ", "")
    if name_no_spaces in text_no_spaces:
        return 15

    # --- LIVELLO 3: KEYWORDS (Fuzzy/Fallback) ---
    keywords = get_canteen_keywords(canteen)
    score = 0
    for kw in keywords:
        if kw in text_norm:
            score += 2
            
    return score