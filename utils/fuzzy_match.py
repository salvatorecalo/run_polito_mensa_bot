from difflib import SequenceMatcher


def fuzzy_match(a: str, b: str, threshold: float = 0.8) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold