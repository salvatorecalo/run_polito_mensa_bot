from database.models import Canteen
from utils import normalize_text

def get_canteen_keywords(canteen: Canteen) -> list[str]:
    # Parole che non aiutano a distinguere le mense
    blacklist = {"mensa", "universitaria", "universitario", "del", "per", "allo", "studio", "edisu"}
    
    # Puliamo il nome: es. "Mensa universitaria Borsellino" -> ["borsellino"]
    full_name = normalize_text(canteen.name)
    words = full_name.split()
    
    if canteen.location_description:
        words += normalize_text(canteen.location_description).split()
        
    # Teniamo solo parole lunghe e non comuni
    keywords = [w for w in words if len(w) > 3 and w not in blacklist]
    
    return keywords