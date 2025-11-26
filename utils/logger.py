"""
Configurazione logging centralizzata
"""

import logging
import sys

# Global flag to ensure we only configure third-party loggers once
_logging_configured = False


class InstagramLogFilter(logging.Filter):
    """Filtro per ridurre il rumore dei log di Instagram API"""

    def filter(self, record: logging.LogRecord) -> bool:
        # Filtra i messaggi di debug di instagrapi
        if record.name.startswith("instagrapi"):
            message = record.getMessage()

            # Pattern specifici da bloccare
            blocked_patterns = [
                "JSONDecodeError",
                "Status 201",
                "public_request",
                "__a=1&__d=dis",
                "challenge_required",
                "login_required",
            ]

            for pattern in blocked_patterns:
                if pattern in message:
                    return False

            # Se è instagrapi, permetti solo WARNING o superiori
            if record.levelno < logging.WARNING:
                return False

        return True


def _configure_instagrapi_silence():
    """Configurazione interna per silenziare instagrapi"""
    global _logging_configured
    if _logging_configured:
        return

    # Lista dei logger di instagrapi da silenziare
    instagrapi_loggers = [
        "instagrapi",
        "instagrapi.mixins",
        "instagrapi.mixins.user",
        "instagrapi.mixins.auth",
        "instagrapi.mixins.challenge",
        "instagrapi.private",
        "urllib3",  # Silenzia anche le richieste HTTP sottostanti
    ]

    instagram_filter = InstagramLogFilter()

    for logger_name in instagrapi_loggers:
        lib_logger = logging.getLogger(logger_name)
        lib_logger.setLevel(logging.ERROR)  # Mostra solo errori gravi
        lib_logger.addFilter(instagram_filter)
        # Impedisce la propagazione al root logger per evitare duplicati indesiderati
        lib_logger.propagate = False

    _logging_configured = True


def setup_logger(name: str = "mensa_bot", level: int = logging.INFO) -> logging.Logger:
    """
    Configura e restituisce un logger con formattazione consistente.

    Args:
        name: Nome del logger
        level: Livello di logging (default: INFO)

    Returns:
        Logger configurato
    """
    # 1. Configura il silenzio per le librerie esterne (una sola volta)
    _configure_instagrapi_silence()

    # 2. Configura il logger dell'applicazione
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evita di aggiungere handler multipli se setup_logger viene chiamato più volte
    if logger.hasHandlers():
        return logger

    # 3. Configura Console Handler
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
