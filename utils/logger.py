"""
Configurazione logging centralizzata
"""

import logging
import sys

def setup_logger(name: str = "mensa_bot", level: int = logging.INFO) -> logging.Logger:
    """
    Configura e restituisce un logger con formattazione consistente.

    Args:
        name: Nome del logger
        level: Livello di logging (default: INFO)

    Returns:
        Logger configurato
    """
    # 1. Configura il logger dell'applicazione
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evita di aggiungere handler multipli se setup_logger viene chiamato più volte
    if logger.hasHandlers():
        return logger

    # 2. Configura Console Handler
    handler = logging.StreamHandler(sys.stdout)

    # Formato: [HH:MM:SS] LEVEL - Message
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Impedisce la propagazione al root logger (evita doppi log se usi uvicorn/gunicorn)
    logger.propagate = False

    return logger
