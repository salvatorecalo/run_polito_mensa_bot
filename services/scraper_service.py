import asyncio
import html
import os
import base64
from typing import List, Optional, Tuple
from datetime import datetime
import requests
from services import AiModel
from utils import normalize_text, store_canteen_match
from utils.file_operations import clean_directory
from utils import get_today_date
from config import DOWNLOAD_DIR, CREATED_IMAGES_DIR
from database.connection import create_db_and_tables, get_session, get_session_maker, init_db
from database.models import Canteen, Menu
from database.repositories import CanteenRepository, MenuRepository
from utils.image_processing import create_long_image
from utils.logger import setup_logger
from services.web_scraping_service import WebScrapingService
import hashlib
import re
from PIL import Image, ImageEnhance, ImageOps

logger = setup_logger(__name__)

_ai_instance = None

def get_ai_model():
    """Restituisce l'istanza dell'AI, creandola solo se non esiste"""
    global _ai_instance
    if _ai_instance is None:
        logger.info("🤖 Primo avvio dell'AI: caricamento Groq in corso...")
        _ai_instance = AiModel()
    return _ai_instance

def preprocess_for_ocr(image_path: str):
    """
        Aumenta il contrasto e la saturazione al massimo cosi da rimuovere i ghirigori
    """
    with Image.open(image_path) as img:
        img = img.convert('L')
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(3.5)
        threshold = 140
        # if the index i is minus than the threshold, the value is black (0) otherwise 255 (white)
        lut = [0 if i < threshold else 255 for i in range(256)]
        img = img.point(lut)
        img.save(image_path, "PNG")
    

def _download_and_ocr_sync(url: str) -> Tuple[Optional[str], bool]:
    """
    Download image and extract text via OCR
    Returns: (extracted_text, is_valid_menu)
    """
    url_hash = hashlib.md5(url.encode()).hexdigest()
    filename = f"story_{url_hash}.jpg"
    path = os.path.join(DOWNLOAD_DIR, filename)

    # Download image
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
        if not os.path.exists(path):
            try:
                logger.info(f"⬇️ Downloading image from {url[:100]}...")
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                with open(path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Preprocessing image for OCR: {path}")
                preprocess_for_ocr(path)
                logger.debug(f"✅ Image saved and cleaned at {path}")
            except Exception as e:
                logger.error(f"❌ Download error for {url[:100]}: {e}")
                return None, False
    ai = get_ai_model()
    # OCR extraction with Groq Llama model
    try:
        text = ai.extracted_text(path)
        if not text:
            return None, False
        logger.debug(f"📝 Local AI extracted {len(text)} characters")
        # Validate menu keywords
        text_normalized = normalize_text(text)
        menu_keywords = ["MENSA UNIVERSITARIA", "MENU", "UNIVERSITY CANTEEN", "EDISU"]
        is_valid_menu = any(keyword in text_normalized for keyword in menu_keywords)

        if not is_valid_menu:
            logger.debug(f"⚠️ Not a valid menu (missing keywords in: {text_normalized[:100]})")
            try:
                os.remove(path)
            except:
                pass
            return None, False  # ✅ Return immediately if invalid

        logger.info(f"✅ Valid menu detected with {len(text)} chars")
        logger.info(f"📝 Extracted text: {text[:500]}...")  # Log first 500 chars
        return text, True

    except Exception as e:
        logger.error(f"❌ OCR error: {e}", exc_info=True)
        try:
            os.remove(path)
        except:
            pass
        return None, False


async def process_image_url(
    url: str,
    all_canteens: List[Canteen],
    menu_repo: MenuRepository,
) -> str:
    """
    Process a single story URL: OCR extraction, canteen matching, DB storage
    Returns: "success" | "skipped" | "error"
    """
    try:
        # Run OCR in thread pool
        text, is_valid_menu = await asyncio.to_thread(_download_and_ocr_sync, url)
        
        # Early exit if not valid
        if not is_valid_menu or not text or len(text.strip()) < 10:
            logger.debug(f"⏭️ Skipping invalid/short content from {url[:50]}")
            return "skipped"

        logger.info(f"📝 Processing valid menu text ({len(text)} chars)")
        text_normalized = normalize_text(text)

        # Detect meal type
        has_pranzo = "PRANZO" in text_normalized or "LUNCH" in text_normalized
        has_cena = "CENA" in text_normalized or "DINNER" in text_normalized

        if not (has_pranzo or has_cena):
            logger.warning(f"⏭️ No meal type keyword found in: {text_normalized[:200]}")
            return "skipped"

        meal_type = "dinner" if has_cena else "lunch"

        # Extract date from text
        date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text_normalized)
        if not date_match:
            logger.warning(f"⏭️ No date found in menu text: {text_normalized[:200]}")
            return "skipped"

        day, month, year = map(int, date_match.groups())
        try:
            from datetime import date
            menu_date = date(year, month, day)
        except ValueError:
            logger.warning(f"⏭️ Invalid date {day}/{month}/{year} in menu text")
            return "skipped"

        if menu_date != get_today_date():
            logger.warning(f"⏭️ Menu date {menu_date} does not match today {get_today_date()}")
            return "skipped"

        # Match canteen using fuzzy matching
        best_match = None
        best_score = 0
        for canteen in all_canteens:
            score = store_canteen_match(text_normalized, canteen)
            logger.debug(f"Score for {canteen.name}: {score}")
            if score > best_score:
                best_score = score
                best_match = canteen

        if not best_match or best_score < 10:
            logger.warning(f"⚠️ No reliable canteen match (best score: {best_score})")
            logger.debug(f"Text sample: {text_normalized[:300]}")
            return "skipped"

        matched_canteen = best_match
        logger.info(f"📍 Matched canteen: {matched_canteen.name} (score={best_score})")

        # Verify canteen has valid ID
        if not matched_canteen.id:
            logger.error(f"❌ Matched canteen '{matched_canteen.name}' has no ID")
            return "error"
        
        img_path = os.path.join(
            CREATED_IMAGES_DIR,
            f"menu_{matched_canteen.id}_{get_today_date().strftime('%Y%m%d')}_{meal_type}.jpg"
        )
        
        menu_text_for_img = f"{matched_canteen.name}\n\n{text}"
        # Puliamo eventuali tag se presenti
        clean_text = html.unescape(re.sub(r'<[^>]+>', '', menu_text_for_img))

        created_path = await create_long_image(
            text=clean_text,
            output_path=img_path,
            logo_text="@RunMensaBot on telegram",
            add_logo=True,
            logo_image_path="assets/run_logo.png"
        )
            
        # Prepare menu data
        courses_json = {
            "raw_lines": [line.strip() for line in text.split("\n") if line.strip()],
            "meta": {
                "source": "web_mirror",
                "url": url,
                "extracted_at": datetime.now().isoformat(),
                "confidence_score": best_score
            }
        }

        # Check if menu already exists
        existing_menu = await menu_repo.get_menu_by_date(
            get_today_date(), 
            matched_canteen.id, 
            meal_type
        )

        if existing_menu:
            # Update existing menu
            logger.info(f"🔄 Updating existing menu for {matched_canteen.name}")
            existing_menu.original_text = text
            existing_menu.image_path = created_path
            existing_menu.courses_json = courses_json
            await menu_repo.update(existing_menu)
        else:
            # Create new menu
            logger.info(f"➕ Creating new menu for {matched_canteen.name}")
            new_menu = Menu(
                canteen_id=matched_canteen.id,
                date=get_today_date(),
                meal_type=meal_type,
                courses_json=courses_json,
                original_text=text,
                image_path=created_path,
                story_id=f"web_{int(datetime.now().timestamp())}_{matched_canteen.id}"
            )
            await menu_repo.create(new_menu)

        logger.info(f"✅ Menu saved successfully for {matched_canteen.name}")
        return "success"

    except Exception as e:
        logger.error(f"❌ Error processing URL {url[:100]}: {e}", exc_info=True)
        return "error"


async def fetch_and_store_menus() -> None:
    """
    Main scraper function: fetch stories, process images, store menus
    """
    logger.info("🚀 Starting Menu Scraper Service...")
    
    # Clean temporary directories
    clean_directory(DOWNLOAD_DIR)
    clean_directory(CREATED_IMAGES_DIR)
    
    # Initialize database
    await init_db()
    await create_db_and_tables()
    
    # Delete existing menus for today to start fresh
    session_maker = get_session_maker()
    session = session_maker()
    try:
        menu_repo = MenuRepository(session)
        await menu_repo.delete_menus_by_date(get_today_date())
        await session.commit()
    finally:
        await session.close()
    
    service = WebScrapingService()

    try:
        # Fetch story URLs from mirror site
        logger.info("🔍 Fetching stories from web mirror...")
        username = os.getenv("TARGET_USER", "edisu_piemonte")
        urls = await service.get_stories_by_browser(username=username)
        
        if not urls:
            logger.warning("⚠️ No story URLs found")
            return
            
        logger.info(f"📸 Found {len(urls)} story URLs to process")

        # Process stories
        async for session in get_session():
            canteen_repo = CanteenRepository(session)
            menu_repo = MenuRepository(session)
            
            # Get all active canteens
            all_canteens = await canteen_repo.get_all_active()
            
            if not all_canteens:
                logger.error("❌ No canteens available, cannot process menus")
                return

            # Process each story URL
            success_count = 0
            skipped_count = 0
            error_count = 0
            
            for i, url in enumerate(urls, 1):
                logger.info(f"📄 Processing story {i}/{len(urls)}")
                result = await process_image_url(url, all_canteens, menu_repo)
                
                if result == "success":
                    success_count += 1
                elif result == "skipped":
                    skipped_count += 1
                else:
                    error_count += 1

            # Final summary
            logger.info("=" * 60)
            logger.info(f"✅ Successfully processed: {success_count}/{len(urls)}")
            logger.info(f"⏭️  Skipped (non-menu): {skipped_count}/{len(urls)}")
            logger.info(f"❌ Errors: {error_count}/{len(urls)}")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Fatal error in scraper: {e}", exc_info=True)
        raise