import unicodedata

def normalize_text(text: str) -> str:
    """
    Convert extracted text to UNICODE
    
    :param text: text to normalize
    :type text: str
    :return: Return the normalize version of the text
    :rtype: str
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode()
    return text.upper()