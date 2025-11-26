"""
Servizio per interazioni con Instagram
"""

import logging
import os
import time
from pathlib import Path
from typing import List

from instagrapi import Client
from instagrapi.exceptions import (
    ChallengeRequired,
    LoginRequired,
    TwoFactorRequired,
    PleaseWaitFewMinutes,
)
from instagrapi.types import Story

from config import IG_PASSWORD, IG_USERNAME, SESSION_FILE
from utils.logger import setup_logger

# Configura logging di instagrapi dopo l'import per ridurre il rumore
logging.getLogger("instagrapi").setLevel(logging.ERROR)

logger = setup_logger(__name__)


class InstagramService:
    """Gestisce autenticazione e operazioni su Instagram"""

    def __init__(self):
        self.client = Client()
        # Imposta delay per evitare rate limiting
        self.client.delay_range = [1, 3]

    def _is_session_valid(self) -> bool:
        """Verifica se la sessione corrente è ancora valida"""
        try:
            # Una chiamata leggera per verificare la validità
            self.client.get_timeline_feed()
            return True
        except (LoginRequired, Exception):
            return False

    def login(self) -> Client:
        """
        Effettua login a Instagram, gestendo intelligentemente la sessione.

        Returns:
            Client Instagram autenticato

        Raises:
            TwoFactorRequired: Se richiesta autenticazione 2FA
            ChallengeRequired: Se richiesta challenge di sicurezza
        """
        session_path = Path(SESSION_FILE)

        # 1. Tentativo caricamento sessione esistente
        if session_path.exists():
            try:
                logger.info("📂 Caricamento sessione da file...")
                self.client.load_settings(session_path)

                if self._is_session_valid():
                    logger.info("✅ Sessione valida, login non necessario")
                    return self.client
                else:
                    logger.warning("⚠️ Sessione scaduta o invalida")
            except Exception as e:
                logger.warning(f"⚠️ Errore caricamento sessione: {e}")

        # 2. Login fresco se sessione non esiste o invalida
        try:
            logger.info(f"🔐 Eseguo login come {IG_USERNAME}...")
            self.client.login(IG_USERNAME, IG_PASSWORD)

            # Salva la nuova sessione
            session_dir = os.path.dirname(SESSION_FILE)
            if session_dir:
                os.makedirs(session_dir, exist_ok=True)

            self.client.dump_settings(session_path)
            logger.info("✅ Login completato e sessione salvata")
            return self.client

        except TwoFactorRequired:
            logger.error(
                "❌ Autenticazione 2FA richiesta. Configura 2FA o disabilitala."
            )
            raise
        except ChallengeRequired:
            logger.error(
                "❌ Challenge richiesta. Accedi via app o browser per risolvere."
            )
            raise
        except PleaseWaitFewMinutes:
            logger.error(
                "⏳ Instagram ha bloccato le richieste temporaneamente (wait feedback)."
            )
            raise
        except Exception as e:
            logger.error(f"❌ Errore critico login Instagram: {e}")
            raise

    def get_user_stories(self, username: str) -> List[Story]:
        """
        Recupera le storie di un utente Instagram.

        Args:
            username: Username Instagram

        Returns:
            Lista di oggetti Story
        """
        if not username:
            raise ValueError("Username non può essere vuoto")

        # Assicura login
        try:
            if not self._is_session_valid():
                self.login()
        except Exception:
            # Se la validazione fallisce, forza il login
            self.login()

        logger.info(f"👤 Cerco storie per: {username}")

        # Logica di retry per errori di rete/JSON (comuni con instagrapi)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Ottieni ID utente
                user_id = self.client.user_id_from_username(username)

                # Ottieni storie
                stories = self.client.user_stories(user_id)
                logger.info(f"📸 Trovate {len(stories)} storie per {username}")
                return stories

            except Exception as e:
                is_json_error = "JSONDecodeError" in str(e) or "Expecting value" in str(
                    e
                )

                if is_json_error and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(
                        f"⚠️ Errore API Instagram (tentativo {attempt + 1}/{max_retries}). "
                        f"Riprovo tra {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                logger.error(f"❌ Errore recupero storie per {username}: {e}")
                raise

        return []
