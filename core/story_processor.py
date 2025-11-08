"""
Logica principale per download e invio storie Instagram
"""
import os
import time
import requests
import cv2
import pytesseract
import googletrans
from typing import List
from instagrapi import Client

from config import TARGET_USER, TELEGRAM_CHAT_ID, DOWNLOAD_DIR, CREATED_IMAGES_DIR
from services import InstagramService, TelegramService
from data.subscribers import load_subscribers
from utils import save_bytes_to_file, clean_directory, create_long_image, setup_logger

logger = setup_logger(__name__)


async def download_and_send_stories(cl: Client) -> None:
    """
    Scarica le storie di TARGET_USER, estrae testo, traduce, crea immagini e invia galleria su Telegram.
    
    Args:
        cl: Client Instagram autenticato
    """
    logger.info("🔎 Avvio download_and_send_stories()...")
    
    async with googletrans.Translator() as translator:
        subscribers = load_subscribers()
        
        # Pulisce le cartelle di download
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        os.makedirs(CREATED_IMAGES_DIR, exist_ok=True)
        
        removed_stories = clean_directory(DOWNLOAD_DIR)
        removed_images = clean_directory(CREATED_IMAGES_DIR)
        logger.info(f"📁 Rimossi {removed_stories} file stories e {removed_images} immagini create")
        
        # --- Scarica stories ---
        try:
            if not TARGET_USER:
                raise ValueError("TARGET_USER non configurato")
            
            logger.info(f"👤 Cerco utente Instagram: {TARGET_USER}")
            user = cl.user_info_by_username(TARGET_USER)
            user_id = user.pk
            logger.info(f"✅ Utente trovato: {user.username} (ID: {user_id})")
            
            stories = cl.user_stories(user_id)
            logger.info(f"📸 Numero di storie trovate: {len(stories)}")
            
        except Exception as e:
            logger.error(f"❌ Errore ottenimento stories: {e}")
            import traceback
            traceback.print_exc()
            return
        
        if not stories:
            logger.warning("⚠️ Nessuna storia disponibile ora.")
            return
        
        images_to_send = []
        
        for s in stories:
            if s.media_type != 1:
                continue
            
            url = s.thumbnail_url
            if not url:
                continue
            
            filename = f"{TARGET_USER}_{s.id}.jpg"
            path = os.path.join(DOWNLOAD_DIR, filename)
            
            try:
                if not os.path.exists(path):
                    logger.info(f"⬇️ Scarico {filename}...")
                    r = requests.get(str(url), timeout=30)
                    r.raise_for_status()
                    save_bytes_to_file(r.content, path)
                else:
                    logger.info(f"✅ Già scaricata: {filename}")
                
                # OCR
                image = cv2.imread(path)
                if image is None:
                    logger.warning(f"⚠️ Impossibile leggere l'immagine: {path}")
                    continue
                
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                extracted_text = pytesseract.image_to_string(gray).strip()
                logger.info(f"🧠 Testo estratto: {extracted_text[:100]}...")
                
                if not extracted_text or len(extracted_text.strip()) < 5:
                    logger.info("🟡 Nessun testo rilevante in questa storia.")
                    continue
                
                # Traduzione
                translated = await translator.translate(extracted_text, dest='en')
                translated_text = translated.text
                
                # Crea immagini testo originale + tradotto
                text_image_path = os.path.join(CREATED_IMAGES_DIR, f"text_{s.id}.jpg")
                translated_image_path = os.path.join(CREATED_IMAGES_DIR, f"translated_{s.id}.jpg")
                
                # Percorso del logo SVG
                logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "logo.svg")
                
                create_long_image(
                    extracted_text, 
                    text_image_path,
                    add_logo=True,
                    logo_image_path=logo_path if os.path.exists(logo_path) else None,
                    logo_position="bottom-right"
                )
                create_long_image(
                    translated_text, 
                    translated_image_path,
                    add_logo=True,
                    logo_image_path=logo_path if os.path.exists(logo_path) else None,
                    logo_position="bottom-right"
                )
                
                images_to_send.extend([text_image_path, translated_image_path])
                logger.info(f"🖼 Create immagini per storia {s.id}")
                
            except Exception as e:
                logger.error(f"❌ Errore durante elaborazione storia: {e}")
                time.sleep(2)
                continue
        
        # --- Invio Telegram ---
        if not images_to_send:
            logger.warning("⚠️ Nessuna immagine da inviare.")
            return
        
        logger.info(f"📤 Invio galleria ({len(images_to_send)} immagini)...")
        
        telegram = TelegramService()
        
        # Invia al chat principale + iscritti
        all_chats = [TELEGRAM_CHAT_ID] + subscribers if TELEGRAM_CHAT_ID else subscribers
        
        for idx, chat_id in enumerate(all_chats):
            try:
                logger.info(f"🚀 Invio galleria a chat_id={chat_id}")
                success = telegram.send_media_group(str(chat_id), images_to_send)
                
                if success:
                    logger.info(f"✅ Invio completato a {chat_id}")
                else:
                    logger.error(f"❌ Invio fallito a {chat_id}")
                
                # Delay tra chat diverse per evitare rate limiting
                if idx < len(all_chats) - 1:
                    logger.info("⏳ Attendo 3s prima del prossimo invio...")
                    time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Errore invio a {chat_id}: {e}")
