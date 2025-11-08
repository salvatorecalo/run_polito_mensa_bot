"""
Gestione iscritti al bot
"""
import json
import os
from typing import List
from config import SUBSCRIBERS_FILE
from utils.logger import setup_logger

logger = setup_logger(__name__)


def load_subscribers() -> List[int]:
    """
    Carica la lista degli iscritti dal file JSON.
    
    Returns:
        Lista di chat_id iscritti
    """
    # Crea directory se non esiste
    os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
    
    if not os.path.exists(SUBSCRIBERS_FILE):
        logger.info("📂 File subscribers non trovato, creato nuovo")
        return []
    
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            
            subscribers = json.loads(content)
            logger.info(f"📋 Caricati {len(subscribers)} iscritti")
            return subscribers
            
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"⚠️ File subscribers corrotto: {e}. Creato nuovo file.")
        return []


def save_subscribers(subscribers: List[int]) -> None:
    """
    Salva la lista degli iscritti su file JSON.
    
    Args:
        subscribers: Lista di chat_id da salvare
    """
    # Crea directory se non esiste
    os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
    
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(subscribers, f, indent=2)
        logger.info(f"💾 Salvati {len(subscribers)} iscritti")
    except Exception as e:
        logger.error(f"❌ Errore salvataggio subscribers: {e}")
        raise


def add_subscriber(chat_id: int) -> bool:
    """
    Aggiunge un iscritto.
    
    Args:
        chat_id: ID della chat da aggiungere
    
    Returns:
        True se aggiunto, False se già presente
    """
    subscribers = load_subscribers()
    
    if chat_id in subscribers:
        return False
    
    subscribers.append(chat_id)
    save_subscribers(subscribers)
    logger.info(f"✅ Nuovo iscritto: {chat_id}")
    return True


def remove_subscriber(chat_id: int) -> bool:
    """
    Rimuove un iscritto.
    
    Args:
        chat_id: ID della chat da rimuovere
    
    Returns:
        True se rimosso, False se non presente
    """
    subscribers = load_subscribers()
    
    if chat_id not in subscribers:
        return False
    
    subscribers.remove(chat_id)
    save_subscribers(subscribers)
    logger.info(f"❌ Iscritto rimosso: {chat_id}")
    return True
