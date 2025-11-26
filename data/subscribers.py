"""
Gestione iscritti al bot (with database support)
"""

import json
import os
from typing import List

from config import SUBSCRIBERS_FILE
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Import repository
try:
    from database.connection import get_session
    from repositories.subscriber_repository import SubscriberRepository

    USE_DATABASE = True
except ImportError:
    USE_DATABASE = False
    logger.warning("⚠️ Database not available, using JSON fallback")


async def load_subscribers_async() -> List[int]:
    """
    Load subscribers from database (async version)
    """
    if not USE_DATABASE:
        return load_subscribers()

    try:
        async for session in get_session():
            repo = SubscriberRepository(session)
            chat_ids = await repo.get_all_chat_ids()
            logger.info(f"📋 Loaded {len(chat_ids)} subscribers from database")
            return chat_ids
    except Exception as e:
        logger.error(f"❌ Database error: {e}, falling back to JSON")
        return load_subscribers()


async def add_subscriber_async(chat_id: int, username: str = None) -> bool:
    """
    Add subscriber to database (async version)
    """
    if not USE_DATABASE:
        return add_subscriber(chat_id)

    try:
        async for session in get_session():
            repo = SubscriberRepository(session)

            # Check if exists
            existing = await repo.get_by_chat_id(chat_id)
            if existing:
                if not existing.is_active:
                    await repo.update_status(chat_id, True)
                    return True
                return False

            # Create new
            await repo.create(chat_id, username)
            return True

    except Exception as e:
        logger.error(f"❌ Database error: {e}, falling back to JSON")
        return add_subscriber(chat_id)


async def remove_subscriber_async(chat_id: int) -> bool:
    """
    Remove subscriber from database (async version)
    """
    if not USE_DATABASE:
        return remove_subscriber(chat_id)

    try:
        async for session in get_session():
            repo = SubscriberRepository(session)
            return await repo.update_status(chat_id, False)

    except Exception as e:
        logger.error(f"❌ Database error: {e}, falling back to JSON")
        return remove_subscriber(chat_id)


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
