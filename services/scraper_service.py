import asyncio
import os
import base64
from typing import List, Optional, Tuple
from datetime import datetime
import requests
from services import AiModel
from utils import normalize_text, store_canteen_match
from utils.file_operations import clean_directory
from utils import TODAY_DATE
from config import DOWNLOAD_DIR, CREATED_IMAGES_DIR
from database.connection import create_db_and_tables, get_session, init_db
from database.models import Canteen, Menu
from database.repositories import CanteenRepository, MenuRepository
from utils.logger import setup_logger
from services.web_scraping_service import WebScrapingService
import hashlib

logger = setup_logger(__name__)

_ai_instance = None

def get_ai_model():
    """Restituisce l'istanza dell'AI, creandola solo se non esiste"""
    global _ai_instance
    if _ai_instance is None:
        from services.ai_model import AiModel
        logger.info("🤖 Primo avvio dell'AI: caricamento Florence-2 in corso...")
        _ai_instance = AiModel()
    return _ai_instance

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
                logger.debug(f"⬇️ Downloading image from {url[:100]}...")
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                with open(path, "wb") as f:
                    f.write(response.content)
                logger.debug(f"✅ Image saved to {path}")
            except Exception as e:
                logger.error(f"❌ Download error for {url[:100]}: {e}")
                return None, False

    ai = get_ai_model()
    # OCR extraction with microsoft florence 2
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

        # Match canteen using fuzzy matching
        best_match = None
        best_score = 0
        for canteen in all_canteens:
            score = store_canteen_match(text_normalized, canteen)
            if score > best_score:
                best_score = score
                best_match = canteen

        if not best_match or best_score < 2:
            logger.warning(f"⚠️ No reliable canteen match (best score: {best_score})")
            logger.debug(f"Text sample: {text_normalized[:300]}")
            return "skipped"

        matched_canteen = best_match
        logger.info(f"📍 Matched canteen: {matched_canteen.name} (score={best_score})")

        # Verify canteen has valid ID
        if not matched_canteen.id:
            logger.error(f"❌ Matched canteen '{matched_canteen.name}' has no ID")
            return "error"

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
            TODAY_DATE, 
            matched_canteen.id, 
            meal_type
        )

        if existing_menu:
            # Update existing menu
            logger.info(f"🔄 Updating existing menu for {matched_canteen.name}")
            existing_menu.original_text = text
            existing_menu.image_path = url
            existing_menu.courses_json = courses_json
            await menu_repo.update(existing_menu)
        else:
            # Create new menu
            logger.info(f"➕ Creating new menu for {matched_canteen.name}")
            new_menu = Menu(
                canteen_id=matched_canteen.id,
                date=TODAY_DATE,
                meal_type=meal_type,
                courses_json=courses_json,
                original_text=text,
                image_path=url,
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