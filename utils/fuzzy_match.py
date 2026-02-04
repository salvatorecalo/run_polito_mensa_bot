from difflib import SequenceMatcher


def fuzzy_match(a: str, b: str, threshold: float = 0.8) -> bool:
    """
    Used to find the right canteen after text extraction
    """
    return SequenceMatcher(None, a, b).ratio() >= threshold