import json
import os
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *


def load_subscribers():
    """
        Funzione che carica gli iscritti
    """
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return []  # file vuoto
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        print("⚠️ File subscribers.json corrotto o vuoto. Ricreato nuovo file.")
        return []

def save_subscribers(subscribers: list):
    """
        Funzione che scrive gli utenti nel file
    """
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subscribers, f)