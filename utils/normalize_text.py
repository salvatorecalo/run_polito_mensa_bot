import unicodedata


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode()
    return text.upper()