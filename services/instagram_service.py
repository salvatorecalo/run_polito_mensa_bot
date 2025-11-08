"""
Servizio per interazioni con Instagram
"""
import os
import logging
from pathlib import Path

# Configura logging di instagrapi prima dell'import
logging.getLogger('instagrapi').setLevel(logging.ERROR)

from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ChallengeRequired
from config import IG_USERNAME, IG_PASSWORD, SESSION_FILE
from utils.logger import setup_logger

logger = setup_logger(__name__)


class InstagramService:
    """Gestisce autenticazione e operazioni su Instagram"""
    
    def __init__(self):
        self.client = None
    
    def login(self) -> Client:
        """
        Effettua login a Instagram, riutilizzando la sessione se disponibile.
        
        Returns:
            Client Instagram autenticato
        
        Raises:
            TwoFactorRequired: Se richiesta autenticazione 2FA
            ChallengeRequired: Se richiesta challenge di sicurezza
        """
        self.client = Client()
        # Prova a caricare sessione esistente
        if os.path.exists(SESSION_FILE):
            try:
                self.client.load_settings(Path(SESSION_FILE))
                logger.info("✅ Sessione Instagram caricata da file")
            except Exception as e:
                logger.warning(f"⚠️ Impossibile caricare sessione: {e}")
        
        # Esegui login
        try:
            self.client.login(IG_USERNAME, IG_PASSWORD)
            
            # Crea directory se non esiste
            session_dir = os.path.dirname(SESSION_FILE)
            if session_dir:
                os.makedirs(session_dir, exist_ok=True)
            
            self.client.dump_settings(Path(SESSION_FILE))
            logger.info("✅ Login Instagram completato")
            return self.client
        except TwoFactorRequired:
            logger.error("❌ Autenticazione 2FA richiesta")
            raise
        except ChallengeRequired:
            logger.error("❌ Challenge Instagram richiesta - accedi via app")
            raise
        except Exception as e:
            logger.error(f"❌ Errore login Instagram: {e}")
            raise
    
    def get_user_stories(self, username: str):
        """
        Recupera le storie di un utente Instagram.
        
        Args:
            username: Username Instagram
        
        Returns:
            Lista di storie
        """
        if not self.client:
            raise RuntimeError("Client non autenticato. Esegui login() prima.")
        
        if not username:
            raise ValueError("Username non può essere None o vuoto")
        
        try:
            logger.info(f"👤 Cerco utente Instagram: {username}")
            
            # Prova a ottenere info utente con retry per JSONDecodeError
            max_retries = 3
            user = None
            
            for attempt in range(max_retries):
                try:
                    user = self.client.user_info_by_username(username)
                    break
                except Exception as e:
                    if "JSONDecodeError" in str(e) and attempt < max_retries - 1:
                        logger.warning(f"⚠️ Tentativo {attempt + 1}/{max_retries} fallito, riprovo...")
                        import time
                        time.sleep(1)  # Breve pausa prima del retry
                        continue
                    raise
            
            if not user:
                raise ValueError(f"Utente {username} non trovato")
                
            user_id = user.pk
            logger.info(f"✅ Utente trovato: {username} (ID: {user_id})")
            
            stories = self.client.user_stories(user_id)
            logger.info(f"📸 Trovate {len(stories)} storie")
            return stories
        except Exception as e:
            if "JSONDecodeError" not in str(e):  # Log solo errori non-JSON
                logger.error(f"❌ Errore recupero storie: {e}")
            raise