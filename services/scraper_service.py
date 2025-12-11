"""
Scraper Service for fetching menus from web mirror and storing them in the Database.
Can be run as a standalone script or scheduled task.
"""

import asyncio
import os
from typing import List, Optional
from datetime import date, datetime
import cv2
import pytesseract
import requests
from googletrans import Translator
import shutil
from config import DOWNLOAD_DIR
from database.connection import create_db_and_tables, get_session, init_db
from database.models import Canteen, Menu
from database.repositories import CanteenRepository, MenuRepository
from utils.logger import setup_logger
from services.web_scraping_service import WebScrapingService

logger = setup_logger(__name__)
translator = Translator()


async def fetch_and_store_menus() -> None:
    """
    Main entry point: Fetches stories, processes them, and upserts into the DB.
    """
    logger.info("🚀 Starting Scraper Service...")

    # 1. Initialize Database
    await init_db()
    await create_db_and_tables()

    service = WebScrapingService()

    # 2. Fetch story URLs from web mirror
    try:
        urls = await service.get_stories_by_browser("edisu_piemonte")
        logger.info(f"📸 Found {len(urls)} story URLs")
        
        if not urls:
            logger.warning("⚠️ No stories found")
            return 
        
        for i, url in enumerate(urls, 1):
            logger.debug(f"  [{i}] {url}...")
        
        async for session in get_session():
            canteen_repo = CanteenRepository(session)
            menu_repo = MenuRepository(session)

            # Load all active canteens for OCR matching
            all_canteens = await canteen_repo.get_all_active()
            
            if not all_canteens:
                logger.error("❌ No canteens configured in DB. Cannot associate menus.")
                logger.info("💡 Creating default canteens...")
                all_canteens = await canteen_repo.seed_default_canteens()
                logger.info(f"✅ Created {len(all_canteens)} default canteens")
            
            logger.info(f"📋 Processing {len(urls)} images against {len(all_canteens)} canteens...")
            success_count = 0
            
            shutil.rmtree(DOWNLOAD_DIR)
            for i, url in enumerate(urls, 1):
                logger.info(f"Processing image {i}/{len(urls)}")
                result = await process_image_url(url, all_canteens, menu_repo, canteen_repo)
                if result:
                    success_count += 1
            
            logger.info(f"✅ Successfully processed {success_count}/{len(urls)} images")
                
        logger.info("✅ Scraper Service completed.")

    except Exception as e:
        logger.error(f"❌ Failed to fetch stories from web mirror: {e}", exc_info=True)
        return


async def process_image_url(
    url: str,
    all_canteens: List[Canteen],
    menu_repo: MenuRepository,
    canteen_repo: CanteenRepository,
) -> bool:
    """
    Download image -> OCR -> Match canteen -> Translate -> Save
    
    Returns:
        True if menu was saved successfully, False otherwise
    """
    try:
        # 1. Download and extract text via OCR
        text = await asyncio.to_thread(_download_and_ocr_sync, url)
        
        if not text or len(text.strip()) < 10:
            logger.debug(f"⏭️ Skipping URL (text too short/empty): {url[:80]}...")
            return False
            
        logger.info(f"📝 Extracted text ({len(text)} chars)")
        text_upper = text.upper()
        
        # 2. Match canteen name in extracted text
        matched_canteen = None
        for canteen in all_canteens:
            # Try both original name and name with spaces instead of underscores
            name_variations = [
                canteen.name.upper(),
                canteen.name.replace("_", " ").upper(),
                canteen.name.replace("_", "").upper()
            ]
            
            for name_variant in name_variations:
                if name_variant in text_upper:
                    matched_canteen = canteen
                    break
            
            if matched_canteen:
                break
                
        if not matched_canteen:
            logger.warning(f"⚠️ No canteen recognized in text for URL: {url[:80]}...")
            logger.debug(f"Text extracted: {text[:200]}...")
            return False
        
        logger.info(f"📍 Canteen recognized: {matched_canteen.name}")
        
        # 3. Determine meal type (lunch/dinner)
        today = date.today()
        meal_type = "lunch"
        
        if "CENA" in text_upper or "DINNER" in text_upper:
            meal_type = "dinner"
        else:
            current_hour = datetime.now().hour
            meal_type = "dinner" if current_hour >= 15 else "lunch"
        
        logger.info(f"🍽️ Meal type detected: {meal_type}")
        
        # 4. Translate text to English (and potentially other languages)
        translated_texts = {}
        try:
            # Translate to English
            result_en = await translator.translate(text, dest='en', src='it')
            translated_texts['en'] = result_en.text
            
            logger.info(f"🌐 Text translated to English")
        except Exception as e:
            logger.warning(f"⚠️ Translation failed: {e}")
            translated_texts = {}
        
        if matched_canteen.id is None:
            return False
        
        # 5. Check if menu already exists
        existing_menu = await menu_repo.get_menu_by_date(
            today, matched_canteen.id, meal_type
        )
        
        courses_json = {
            "raw_lines": [line.strip() for line in text.split("\n") if line.strip()],
            "meta": {
                "source": "web_mirror",
                "url": url,
                "extracted_at": datetime.now().isoformat()
            },
            "translations": translated_texts
        }

        if existing_menu:
            logger.info(f"🔄 Updating existing menu for {matched_canteen.name} ({meal_type})")
            existing_menu.original_text = text
            existing_menu.image_path = url
            existing_menu.courses_json = courses_json
            existing_menu.translated_text = translated_texts.get('en', '')
            await menu_repo.update(existing_menu)
        else:
            logger.info(f"➕ Creating new menu for {matched_canteen.name} ({meal_type})")
            new_menu = Menu(
                canteen_id=matched_canteen.id if matched_canteen.id is not None else 1,
                date=today,
                meal_type=meal_type,
                courses_json=courses_json,
                original_text=text,
                translated_text=translated_texts.get('en', ''),
                image_path=url,
                story_id=f"web_{int(datetime.now().timestamp())}"
            )
            await menu_repo.create(new_menu)
            
        logger.info(f"✅ Menu saved successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error processing URL {url}...: {e}", exc_info=True)
        return False


def _download_and_ocr_sync(url: str) -> Optional[str]:
    """
    Synchronous helper for downloading and OCR.
    Executed in a separate thread to avoid blocking the async event loop.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    # Generate filename from URL hash to avoid duplicates
    import hashlib
    url_hash = hashlib.md5(url.encode()).hexdigest()
    filename = f"story_{url_hash}.jpg"
    path = os.path.join(DOWNLOAD_DIR, filename)

    # 1. Download image if not already cached
    if not os.path.exists(path):
        try:
            logger.debug(f"⬇️ Downloading image from {url[:80]}...")
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            with open(path, "wb") as f:
                f.write(response.content)
            logger.debug(f"✅ Image saved to {path}")
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return None
    else:
        logger.debug(f"♻️ Using cached image: {path}")

    # 2. OCR extraction
    try:
        image = cv2.imread(path)
        if image is None:
            logger.error(f"❌ Failed to read image: {path}")
            return None

        # Preprocessing for better OCR
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply thresholding to binarize image
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        # Extract text with Italian language hint
        text = pytesseract.image_to_string(
            thresh, 
            lang='ita',  # Use Italian language model
            config='--psm 6'  # Assume uniform block of text
        ).strip()
        
        if text:
            logger.debug(f"📝 OCR extracted {len(text)} characters")
        else:
            logger.warning(f"⚠️ OCR extracted no text from {path}")
        
        return text
        
    except Exception as e:
        logger.error(f"❌ OCR error: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    try:
        asyncio.run(fetch_and_store_menus())
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")