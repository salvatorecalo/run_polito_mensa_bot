from database.models import Canteen
from utils.get_canteen_keywords import get_canteen_keywords
from utils import fuzzy_match, normalize_text
from utils.logger import setup_logger
import re

logger = setup_logger(__name__)


def store_canteen_match(text: str, canteen: Canteen):
    text_norm = normalize_text(text)
    name_norm = normalize_text(canteen.name)
    
    # --- LIVELLO 1: IL NOME SPECIFICO (Fuzzy Word-by-Word) ---
    # Prendiamo l'ultima parola (es: "Borsellino", "Braccini")
    specific_name = name_norm.split()[-1]
    
    # Dividiamo il testo OCR in parole pulite
    words_in_text = re.findall(r'\w+', text_norm)
    
    for word in words_in_text:
        # Applichiamo il TUO fuzzy_match su ogni parola del testo
        if len(word) >= 4 and fuzzy_match(specific_name, word, threshold=0.8):
            logger.info(f"🎯 Match trovato: {specific_name} identificato come '{word}'")
            return 20 # Vittoria immediata

    # --- LIVELLO 2: NOME COMPLETO SENZA SPAZI (Backup per nomi composti) ---
    text_no_spaces = text_norm.replace(" ", "")
    name_no_spaces = name_norm.replace(" ", "")
    if name_no_spaces in text_no_spaces:
        return 15

    # --- LIVELLO 3: KEYWORDS (Fuzzy/Fallback) ---
    keywords = get_canteen_keywords(canteen)
    score = 0
    for kw in keywords:
        if normalize_text(kw) in text_norm:
            score += 3
            
    return score