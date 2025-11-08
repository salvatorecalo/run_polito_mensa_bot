"""
Servizio per invio messaggi Telegram
"""
import json
import time
import requests
from typing import List, Optional
from config import TELEGRAM_TOKEN, TELEGRAM_BATCH_SIZE
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Configurazione rate limiting
MAX_RETRIES = 3
BASE_DELAY = 2  # secondi tra invii
RATE_LIMIT_DELAY = 5  # secondi extra quando si riceve 429


class TelegramService:
    """Gestisce l'invio di messaggi e media su Telegram"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or TELEGRAM_TOKEN
        if not self.token:
            raise ValueError("TELEGRAM_TOKEN non configurato")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, chat_id: str, text: str) -> bool:
        """
        Invia un messaggio di testo a una chat Telegram.
        
        Args:
            chat_id: ID della chat destinataria
            text: Testo del messaggio
        
        Returns:
            True se l'invio è riuscito
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ Errore invio messaggio: {e}")
            return False
    
    def send_media_group(self, chat_id: str, image_paths: List[str]) -> bool:
        """
        Invia un gruppo di immagini a una chat Telegram.
        Divide automaticamente in batch se supera il limite di Telegram.
        Gestisce automaticamente il rate limiting con retry.
        
        Args:
            chat_id: ID della chat destinataria
            image_paths: Lista di percorsi delle immagini da inviare
        
        Returns:
            True se l'invio è riuscito, False altrimenti
        """
        if not image_paths:
            logger.warning("⚠️ Nessuna immagine da inviare")
            return False
        
        logger.info(f"📤 Invio {len(image_paths)} immagini a chat_id={chat_id}")
        
        try:
            # Dividi in batch per rispettare il limite Telegram
            for batch_idx, start in enumerate(range(0, len(image_paths), TELEGRAM_BATCH_SIZE)):
                batch = image_paths[start:start + TELEGRAM_BATCH_SIZE]
                
                # Retry con exponential backoff
                success = False
                for attempt in range(MAX_RETRIES):
                    result = self._send_batch(chat_id, batch)
                    
                    if result["success"]:
                        success = True
                        break
                    elif result["rate_limited"]:
                        # Rate limiting: aspetta più a lungo
                        retry_after = result.get("retry_after", RATE_LIMIT_DELAY)
                        logger.warning(f"⏳ Rate limit raggiunto, attendo {retry_after}s prima del retry {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(retry_after)
                    else:
                        # Altro errore: exponential backoff
                        wait_time = BASE_DELAY * (2 ** attempt)
                        logger.warning(f"⏳ Errore invio, retry {attempt + 1}/{MAX_RETRIES} tra {wait_time}s")
                        time.sleep(wait_time)
                
                if not success:
                    logger.error(f"❌ Invio fallito dopo {MAX_RETRIES} tentativi")
                    return False
                
                # Delay tra batch per evitare rate limiting
                if batch_idx < (len(image_paths) // TELEGRAM_BATCH_SIZE):
                    time.sleep(BASE_DELAY)
            
            logger.info(f"✅ Invio completato a chat_id={chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Errore invio media group: {e}")
            return False
    
    def _send_batch(self, chat_id: str, image_paths: List[str]) -> dict:
        """
        Invia un singolo batch di immagini.
        
        Args:
            chat_id: ID della chat
            image_paths: Lista di percorsi immagini (max 10)
        
        Returns:
            Dict con:
            - success (bool): True se successo
            - rate_limited (bool): True se errore 429
            - retry_after (int): Secondi da attendere prima del retry
        """
        media_group = []
        files = {}
        
        # Prepara media group
        for i, img_path in enumerate(image_paths):
            attach_name = f"file{i}"
            media_group.append({
                "type": "photo",
                "media": f"attach://{attach_name}"
            })
            files[attach_name] = open(img_path, "rb")
        
        # Invia richiesta
        payload = {
            "chat_id": chat_id,
            "media": json.dumps(media_group)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/sendMediaGroup",
                data=payload,
                files=files,
                timeout=30
            )
            
            logger.info(f"📦 Batch inviato (status {response.status_code})")
            
            if response.status_code == 200:
                return {"success": True, "rate_limited": False}
            
            # Gestione rate limiting (429)
            if response.status_code == 429:
                try:
                    error_data = response.json()
                    retry_after = error_data.get("parameters", {}).get("retry_after", RATE_LIMIT_DELAY)
                    logger.warning(f"⚠️ Rate limit: retry dopo {retry_after}s")
                    return {
                        "success": False,
                        "rate_limited": True,
                        "retry_after": retry_after
                    }
                except Exception:
                    return {
                        "success": False,
                        "rate_limited": True,
                        "retry_after": RATE_LIMIT_DELAY
                    }
            
            # Altri errori
            logger.error(f"❌ Errore Telegram: {response.text}")
            return {"success": False, "rate_limited": False}
            
        except Exception as e:
            logger.error(f"❌ Errore invio batch: {e}")
            return {"success": False, "rate_limited": False}
        finally:
            # Chiudi tutti i file aperti
            for f in files.values():
                f.close()
