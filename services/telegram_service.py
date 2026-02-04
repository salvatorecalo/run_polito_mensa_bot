"""
Service for Telegram interactions (Async version)
"""

import asyncio
import json
from typing import List, Optional

import httpx

from config import TELEGRAM_BATCH_SIZE, TELEGRAM_TOKEN
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Configurazione rate limiting
MAX_RETRIES = 3
BASE_DELAY = 2  # secondi tra invii
RATE_LIMIT_DELAY = 5  # secondi extra quando si riceve 429


class TelegramService:
    """Handles sending messages and media to Telegram asynchronously"""

    BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

    def __init__(self):
        # Timeout configuration for httpx
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    async def send_message(self, chat_id: str | int, text: str) -> bool:
        """Send a text message"""
        url = f"{self.BASE_URL}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"❌ Error sending message to {chat_id}: {e}")
                return False

    async def send_photo(
        self, chat_id: str | int, photo_path: str, caption: Optional[str] = None
    ) -> bool:
        """Send a photo"""
        url = f"{self.BASE_URL}/sendPhoto"
        logger.info(f"URL PHOTO {url}")
        data = {"chat_id": str(chat_id), "parse_mode": "Markdown"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Open file in binary mode
                with open(photo_path, "rb") as f:
                    files = {"photo": f}
                    response = await client.post(url, data=data, files=files)
                    response.raise_for_status()
                return True
            except Exception as e:
                logger.error(f"❌ Error sending photo to {chat_id}: {e}")
                return False

    async def send_media_group(self, chat_id: str | int, image_paths: List[str]) -> bool:
        """
        Invia un gruppo di immagini a una chat Telegram.
        Gestisce automaticamente batching, async e rate limiting.
        """
        if not image_paths:
            logger.warning("⚠️ Nessuna immagine da inviare")
            return False

        logger.info(f"📤 Invio {len(image_paths)} immagini a chat_id={chat_id}")

        try:
            # Dividi in batch per rispettare il limite Telegram
            for batch_idx, start in enumerate(
                range(0, len(image_paths), TELEGRAM_BATCH_SIZE)
            ):
                batch = image_paths[start : start + TELEGRAM_BATCH_SIZE]

                # Retry con exponential backoff
                success = False
                for attempt in range(MAX_RETRIES):
                    result = await self._send_batch(chat_id, batch)

                    if result["success"]:
                        success = True
                        break
                    elif result["rate_limited"]:
                        # Rate limiting: aspetta più a lungo
                        retry_after = result.get("retry_after", RATE_LIMIT_DELAY)
                        logger.warning(
                            f"⏳ Rate limit raggiunto, attendo {retry_after}s prima del retry {attempt + 1}/{MAX_RETRIES}"
                        )
                        await asyncio.sleep(retry_after)
                    else:
                        # Altro errore: exponential backoff
                        wait_time = BASE_DELAY * (2**attempt)
                        logger.warning(
                            f"⏳ Errore invio, retry {attempt + 1}/{MAX_RETRIES} tra {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)

                if not success:
                    logger.error(f"❌ Invio fallito dopo {MAX_RETRIES} tentativi")
                    return False

                # Delay tra batch per evitare rate limiting
                if batch_idx < (len(image_paths) // TELEGRAM_BATCH_SIZE):
                    await asyncio.sleep(BASE_DELAY)

            logger.info(f"✅ Invio completato a chat_id={chat_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Errore invio media group: {e}")
            return False

    async def _send_batch(self, chat_id: str | int, image_paths: List[str]) -> dict:
        """
        Invia un singolo batch di immagini (Async).
        """
        media_group = []
        files = []
        file_handles = []

        try:
            # Prepara media group e file handles
            for i, img_path in enumerate(image_paths):
                attach_name = f"file{i}"
                media_group.append({
                    "type": "photo", 
                    "media": f"attach://{attach_name}"
                })
                
                # Apri file e tienilo tracciato per chiuderlo dopo
                f = open(img_path, "rb")
                file_handles.append(f)
                files.append((attach_name, f))

            payload = {
                "chat_id": str(chat_id), 
                "media": json.dumps(media_group)
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.BASE_URL}/sendMediaGroup", 
                    data=payload, 
                    files=files
                )

                if response.status_code == 200:
                    return {"success": True, "rate_limited": False}

                # Gestione rate limiting (429)
                if response.status_code == 429:
                    try:
                        error_data = response.json()
                        retry_after = error_data.get("parameters", {}).get(
                            "retry_after", RATE_LIMIT_DELAY
                        )
                        return {
                            "success": False,
                            "rate_limited": True,
                            "retry_after": retry_after,
                        }
                    except Exception:
                        return {
                            "success": False,
                            "rate_limited": True,
                            "retry_after": RATE_LIMIT_DELAY,
                        }

                logger.error(f"❌ Errore Telegram: {response.text}")
                return {"success": False, "rate_limited": False}

        except Exception as e:
            logger.error(f"❌ Errore invio batch: {e}")
            return {"success": False, "rate_limited": False}
        finally:
            # Chiudi tutti i file aperti
            for f in file_handles:
                f.close()