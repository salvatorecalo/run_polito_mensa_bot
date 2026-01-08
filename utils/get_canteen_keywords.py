from database.models import Canteen
from utils import normalize_text


def get_canteen_keywords(canteen: Canteen) -> list[str]:
    # Prendi parole significative dal nome e dalla location
    words = normalize_text(canteen.name).split()
    if canteen.location_description:
        words += normalize_text(canteen.location_description).split()
    # Ignora parole troppo corte tipo 'di', 'al'
    return [w for w in words if len(w) > 2]