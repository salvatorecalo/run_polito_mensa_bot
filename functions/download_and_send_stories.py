import os
import time
import json
import googletrans
from config import *
from instagrapi import Client
import requests
import cv2
import pytesseract
from functions.save_bytes_to_file import *
from functions.subscribers import load_subscribers
from PIL import Image, ImageDraw, ImageFont

from PIL import Image, ImageDraw, ImageFont

def create_long_image(text: str, output_path: str, width=1080, min_font=300, max_font=500):
    """
    Crea un'unica immagine verticale (1080x1920) con tutto il testo dentro.
    Nessuna divisione in più slide. Adatta automaticamente la dimensione del font.
    """
    text = text.strip().upper()
    bg_color = (255, 140, 0)  # arancione
    text_color = (255, 255, 255)  # bianco
    height = 1920

    # Trova un font disponibile
    try:
        font_path = "arialbd.ttf"
        font = ImageFont.truetype(font_path, max_font)
    except:
        font = ImageFont.load_default()

    # Adatta il font per far entrare tutto il testo
    image = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)

    # riduce font se il testo non entra
    while True:
        bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if text_width <= width - 100 and text_height <= height - 100:
            break
        if font.size <= min_font:
            break
        font = ImageFont.truetype(font_path, font.size - 10)

    # centrato al centro dell’immagine
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.multiline_text((x, y), text, fill=text_color, font=font, align="center")

    image.save(output_path)
    return output_path

async def download_and_send_stories(cl: Client) -> None:
    """
    Scarica le storie di TARGET_USER, estrae testo, traduce, crea immagini e invia galleria su Telegram.
    """
    print("🔎 Avvio download_and_send_stories()...")

    async with googletrans.Translator() as translator:
        subscribers = load_subscribers()

        # Pulisce la cartella download
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        for filename in os.listdir("created_images"):
            file_path = os.path.join("created_images", filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("📁 Cartella stories scaricate pulita.")
        print("📁 Cartella created_images scaricate pulita.")

        # --- Scarica stories ---
        try:
            print(f"👤 Cerco utente Instagram: {TARGET_USER}")
            user = cl.user_info_by_username(TARGET_USER)
            user_id = user.pk
            print(f"✅ Utente trovato: {user.username} (ID: {user_id})")

            stories = cl.user_stories(user_id)
            print(f"📸 Numero di storie trovate: {len(stories)}")

        except Exception as e:
            print("❌ Errore ottenimento stories:", e)
            import traceback; traceback.print_exc()
            return

        if not stories:
            print("⚠️ Nessuna storia disponibile ora.")
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
                    print(f"⬇️ Scarico {filename}...")
                    r = requests.get(url, timeout=30)
                    r.raise_for_status()
                    save_bytes_to_file(r.content, path)
                else:
                    print(f"✅ Già scaricata: {filename}")

                # OCR
                image = cv2.imread(path)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                extracted_text = pytesseract.image_to_string(gray).strip()
                print(f"🧠 Testo estratto: {extracted_text[:100]}...")

                if not extracted_text or len(extracted_text.strip()) < 5:
                    print("🟡 Nessun testo rilevante in questa storia.")
                    continue

                # Traduzione
                translated = await translator.translate(extracted_text, dest='en')
                translated_text = translated.text

                # Crea immagini testo originale + tradotto
                text_image_path = os.path.join("created_images", f"text_{s.id}.jpg")
                translated_image_path = os.path.join("created_images", f"translated_{s.id}.jpg")

                create_long_image(extracted_text, text_image_path)
                create_long_image(translated_text, translated_image_path)

                images_to_send.extend([text_image_path, translated_image_path])
                print(f"🖼 Create immagini per storia {s.id}")

            except Exception as e:
                print(f"❌ Errore durante elaborazione storia: {e}")
                time.sleep(2)
                continue

        # --- Invio Telegram ---
        if not images_to_send:
            print("⚠️ Nessuna immagine da inviare.")
            return

        print(f"📤 Invio galleria ({len(images_to_send)} immagini)...")
        batch_size = 10  # Telegram limita a 10 per gruppo

        for chat_id in [TELEGRAM_CHAT_ID] + subscribers:
            try:
                print(f"🚀 Invio galleria a chat_id={chat_id}")

                for start in range(0, len(images_to_send), batch_size):
                    batch = images_to_send[start:start + batch_size]
                    media_group = []
                    files = {}

                    for i, img_path in enumerate(batch):
                        attach_name = f"file{i}"
                        media_group.append({
                            "type": "photo",
                            "media": f"attach://{attach_name}"
                        })
                        files[attach_name] = open(img_path, "rb")

                    payload = {
                        "chat_id": chat_id,
                        "media": json.dumps(media_group)
                    }

                    r = requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMediaGroup",
                        data=payload,
                        files=files
                    )

                    print(f"📦 Batch inviato (status {r.status_code})")
                    print("📨 Risposta Telegram:", r.text)

                    if r.status_code != 200:
                        print("❌ Errore Telegram:", r.text)

                    # Chiude i file
                    for f in files.values():
                        f.close()

                    time.sleep(1)

            except Exception as e:
                print(f"❌ Errore invio a {chat_id}: {e}")
