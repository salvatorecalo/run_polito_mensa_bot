"""
Configurazione logging centralizzata
"""
import logging
from datetime import datetime

class InstagramLogFilter(logging.Filter):
    """Filtro per ridurre il rumore dei log di Instagram API"""
    
    def filter(self, record):
        # Filtra i messaggi di debug di instagrapi
        if record.name.startswith('instagrapi'):
            # Filtra tutti i messaggi che contengono questi pattern
            message = record.getMessage()
            blocked_patterns = [
                'JSONDecodeError',
                'Status 201',
                'public_request',
                '__a=1&__d=dis'
            ]
            
            for pattern in blocked_patterns:
                if pattern in message:
                    return False
            
            # Permetti solo errori gravi
            if record.levelno < logging.ERROR:
                return False
        return True

def configure_global_logging():
    """Configura il logging globale per ridurre il rumore di instagrapi"""
    
    # Disabilita completamente certi logger rumorosi
    logging.getLogger('instagrapi').setLevel(logging.CRITICAL)
    logging.getLogger('instagrapi.mixins').setLevel(logging.CRITICAL)
    logging.getLogger('instagrapi.mixins.user').setLevel(logging.CRITICAL)
    logging.getLogger('instagrapi.private').setLevel(logging.CRITICAL)
    
    # Applica il filtro al root logger
    root_logger = logging.getLogger()
    instagram_filter = InstagramLogFilter()
    
    for handler in root_logger.handlers:
        handler.addFilter(instagram_filter)

def setup_logger(name: str = "mensa_bot", level: int = logging.INFO) -> logging.Logger:
    """
    Configura e restituisce un logger con formattazione consistente.
    
    Args:
        name: Nome del logger
        level: Livello di logging (default: INFO)
    
    Returns:
        Logger configurato
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Evita duplicazione handler se già configurato
    if logger.handlers:
        return logger
    
    # Console handler
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Aggiungi filtro per ridurre rumore Instagram
    instagram_filter = InstagramLogFilter()
    handler.addFilter(instagram_filter)
    
    logger.addHandler(handler)
    
    # Configura logger di instagrapi per ridurre il rumore
    instagrapi_logger = logging.getLogger('instagrapi')
    instagrapi_logger.setLevel(logging.ERROR)  # Solo errori gravi
    instagrapi_logger.addFilter(instagram_filter)
    
    # Configura anche il logger root di instagrapi per i moduli specifici
    for module in ['instagrapi.mixins', 'instagrapi.mixins.user', 'instagrapi.private']:
        mod_logger = logging.getLogger(module)
        mod_logger.setLevel(logging.ERROR)
        mod_logger.addFilter(instagram_filter)
    
    return logger