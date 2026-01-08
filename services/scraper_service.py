import unicodedata
import asyncio
import os
import base64
from typing import List, Optional, Tuple
from datetime import date, datetime
import cv2
import pytesseract
import requests
from difflib import SequenceMatcher
from utils.file_operations import clean_directory

from config import DOWNLOAD_DIR
from database.connection import create_db_and_tables, get_session, init_db
from database.models import Canteen, Menu
from database.repositories import CanteenRepository, MenuRepository
from utils.logger import setup_logger
from services.web_scraping_service import WebScrapingService

logger = setup_logger(__name__)

# ---------------- Fuzzy Matching ----------------
def fuzzy_match(a: str, b: str, threshold: float = 0.8) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold

# ---------------- Normalize Text ----------------
def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode()
    return text.upper()

# ---------------- Get Canteen Keywords ----------------

def get_canteen_keywords(canteen: Canteen) -> list[str]:
    # Prendi parole significative dal nome e dalla location
    words = normalize_text(canteen.name).split()
    if canteen.location_description:
        words += normalize_text(canteen.location_description).split()
    # Ignora parole troppo corte tipo 'di', 'al'
    return [w for w in words if len(w) > 2]

# ---------------- OCR + Download ----------------
def _download_and_ocr_sync(url: str) -> Tuple[Optional[str], bool]:
    import hashlib

    url_hash = hashlib.md5(url.encode()).hexdigest()
    filename = f"story_{url_hash}.jpg"
    path = os.path.join(DOWNLOAD_DIR, filename)

    # --- Handle base64 images ---
    if url.startswith("data:image"):
        try:
            header, encoded = url.split(",", 1)
            data = base64.b64decode(encoded)
            with open(path, "wb") as f:
                f.write(data)
            logger.debug(f"✅ Base64 image saved to {path}")
        except Exception as e:
            logger.error(f"❌ Failed to decode base64 image: {e}")
            return None, False
    else:
        # --- Download HTTP images ---
        if not os.path.exists(path):
            try:
                logger.debug(f"⬇️ Downloading image...")
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                with open(path, "wb") as f:
                    f.write(response.content)
                logger.debug(f"✅ Image saved to {path}")
            except Exception as e:
                logger.error(f"❌ Download error: {e}")
                return None, False

    # --- OCR Preprocessing ---
    try:
        image = cv2.imread(path)
        if image is None:
            logger.error(f"❌ Failed to read image: {path}")
            try:
                os.remove(path)
            except: pass
            return None, False

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 3)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, lang='ita', config='--psm 6').strip()
        logger.debug(f"📝 OCR extracted {len(text)} characters")

        # --- Validate menu keywords ---
        text_normalized = normalize_text(text)
        menu_keywords = ["MENSA UNIVERSITARIA", "MENU", "UNIVERSITY CANTEEN"]
        is_valid_menu = any(keyword in text_normalized for keyword in menu_keywords)

        if not is_valid_menu:
            logger.debug(f"⚠️ Not a valid menu (missing keywords)")
            os.remove(path)

        return text, is_valid_menu

    except Exception as e:
        logger.error(f"❌ OCR error: {e}", exc_info=True)
        return None, False

# ---------------- Process Image URL ----------------
async def process_image_url(
    url: str,
    all_canteens: List[Canteen],
    menu_repo: MenuRepository,
) -> str:
    try:
        text, is_valid_menu = await asyncio.to_thread(_download_and_ocr_sync, url)
        if not is_valid_menu or not text or len(text.strip()) < 10:
            return "skipped"

        logger.info(f"📝 Extracted valid menu text ({len(text)} chars)")
        text_normalized = normalize_text(text)

        # Meal type detection
        has_pranzo = "PRANZO" in text_normalized or "LUNCH" in text_normalized
        has_cena = "CENA" in text_normalized or "DINNER" in text_normalized

        if not (has_pranzo or has_cena):
            logger.warning("⏭️ No meal type keyword found")
            return "skipped"

        # Match canteen using fuzzy matching
        matched_canteen = None
        for canteen in all_canteens:
            keywords = get_canteen_keywords(canteen)
            for kw in keywords:
                if kw in text_normalized:
                    matched_canteen = canteen
                    break
            if matched_canteen: break

        if not matched_canteen:
            logger.warning(f"⚠️ No canteen recognized in text: {text[:200]}")
            return "error"

        logger.info(f"📍 Canteen recognized: {matched_canteen.name}")

        today = date.today()
        meal_type = "dinner" if has_cena else "lunch"

        # Check if menu exists
        existing_menu = await menu_repo.get_menu_by_date(today, matched_canteen.id, meal_type)
        courses_json = {
            "raw_lines": [line.strip() for line in text.split("\n") if line.strip()],
            "meta": {"source": "web_mirror", "url": url, "extracted_at": datetime.now().isoformat()}
        }

        if existing_menu:
            existing_menu.original_text = text
            existing_menu.image_path = url
            existing_menu.courses_json = courses_json
            await menu_repo.update(existing_menu)
        else:
            new_menu = Menu(
                canteen_id=matched_canteen.id,
                date=today,
                meal_type=meal_type,
                courses_json=courses_json,
                original_text=text,
                translated_text="",
                image_path=url,
                story_id=f"web_{int(datetime.now().timestamp())}"
            )
            await menu_repo.create(new_menu)

        logger.info("✅ Menu saved successfully")
        return "success"

    except Exception as e:
        logger.error(f"❌ Error processing URL: {e}", exc_info=True)
        return "error"

# ---------------- Main Scraper ----------------
async def fetch_and_store_menus() -> None:
    logger.info("🚀 Starting Scraper Service...")
    clean_directory(DOWNLOAD_DIR)

    await init_db()
    await create_db_and_tables()
    service = WebScrapingService()

    try:
        urls = await service.get_stories_by_browser("edisu_piemonte")
        logger.info(f"📸 Found {len(urls)} story URLs")
        if not urls: return

        async for session in get_session():
            canteen_repo = CanteenRepository(session)
            menu_repo = MenuRepository(session)

            all_canteens = await canteen_repo.get_all_active()
            if not all_canteens:
                all_canteens = await canteen_repo.seed_default_canteens()

            success_count = skipped_count = 0
            for i, url in enumerate(urls, 1):
                result = await process_image_url(url, all_canteens, menu_repo)
                if result == "success": success_count += 1
                elif result == "skipped": skipped_count += 1

            logger.info(f"✅ Processed {success_count}/{len(urls)} images successfully")
            logger.info(f"⏭️ Skipped {skipped_count} non-menu images")

    except Exception as e:
        logger.error(f"❌ Failed to fetch stories: {e}", exc_info=True)
