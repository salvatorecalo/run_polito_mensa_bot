"""
Scraper Service for fetching menus from web mirror and storing them in the Database.
Can be run as a standalone script or scheduled task.
"""

import asyncio
import os
from typing import List, Optional, Tuple
from datetime import date, datetime
import cv2
import pytesseract
import requests
from utils.file_operations import clean_directory

from config import DOWNLOAD_DIR
from database.connection import create_db_and_tables, get_session, init_db
from database.models import Canteen, Menu
from database.repositories import CanteenRepository, MenuRepository
from utils.logger import setup_logger
from services.web_scraping_service import WebScrapingService

logger = setup_logger(__name__)

async def fetch_and_store_menus() -> None:
    """
    Main entry point: Fetches stories, processes them, and upserts into the DB.
    """
    logger.info("🚀 Starting Scraper Service...")
    clean_directory(DOWNLOAD_DIR)
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
            logger.debug(f"  [{i}] {url}")
        
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
            skipped_count = 0
            
            for i, url in enumerate(urls, 1):
                logger.info(f"Processing image {i}/{len(urls)}")
                result = await process_image_url(url, all_canteens, menu_repo)
                
                if result == "success":
                    success_count += 1
                elif result == "skipped":
                    skipped_count += 1
            
            logger.info(f"✅ Successfully processed {success_count}/{len(urls)} images")
            logger.info(f"⏭️ Skipped {skipped_count} non-menu images")
                
        logger.info("✅ Scraper Service completed.")

    except Exception as e:
        logger.error(f"❌ Failed to fetch stories from web mirror: {e}", exc_info=True)


async def process_image_url(
    url: str,
    all_canteens: List[Canteen],
    menu_repo: MenuRepository,
) -> str:
    """
    Download image -> OCR -> Match canteen -> Save
    
    Returns:
        "success" if menu was saved successfully
        "skipped" if image was not a menu
        "error" if processing failed
    """
    try:
        # 1. Download and extract text via OCR
        text, is_valid_menu = await asyncio.to_thread(_download_and_ocr_sync, url)
        
        # 2. Validate that this is actually a menu
        if not is_valid_menu:
            logger.info(f"⏭️ Skipping URL (not a menu - missing 'Mensa Universitaria')")
            return "skipped"
        
        if not text or len(text.strip()) < 10:
            logger.debug(f"⏭️ Skipping URL (text too short/empty)")
            return "skipped"
            
        logger.info(f"📝 Extracted valid menu text ({len(text)} chars)")
        text_upper = text.upper()
        
        # 3. Check for meal type keywords (IN ITALIAN - the original language!)
        has_pranzo = "PRANZO" in text_upper or "LUNCH" in text_upper
        has_cena = "CENA" in text_upper or "DINNER" in text_upper
        
        if not (has_pranzo or has_cena):
            logger.warning(f"⏭️ Skipping URL (no 'pranzo' or 'cena' found)")
            return "skipped"
        
        # 4. Match canteen name in extracted text
        matched_canteen = None
        for canteen in all_canteens:
            # Try multiple name variations
            name_variations = [
                canteen.name.upper(),
                canteen.name.replace("_", " ").upper(),
                canteen.name.replace("_", "").upper(),
                canteen.location_description.upper() if canteen.location_description else ""
            ]
            
            for name_variant in name_variations:
                if name_variant and name_variant in text_upper:
                    matched_canteen = canteen
                    break
            
            if matched_canteen:
                break

        if not matched_canteen:
            logger.warning(f"⚠️ No canteen recognized in text")
            logger.debug(f"Text sample: {text[:200]}...")
            return "error"
        
        logger.info(f"📍 Canteen recognized: {matched_canteen.name}")
        
        # 5. Determine meal type
        today = date.today()
        
        if has_cena:
            meal_type = "dinner"
        elif has_pranzo:
            meal_type = "lunch"
        else:
            # Fallback to time-based detection
            current_hour = datetime.now().hour
            meal_type = "dinner" if current_hour >= 15 else "lunch"
        
        logger.info(f"🍽️ Meal type detected: {meal_type}")
        
        if matched_canteen.id is None:
            logger.error("❌ Matched canteen has no ID")
            return "error"
        
        # 6. Check if menu already exists
        existing_menu = await menu_repo.get_menu_by_date(
            today, matched_canteen.id, meal_type
        )
        
        courses_json = {
            "raw_lines": [line.strip() for line in text.split("\n") if line.strip()],
            "meta": {
                "source": "web_mirror",
                "url": url,
                "extracted_at": datetime.now().isoformat()
            }
        }

        if existing_menu:
            logger.info(f"🔄 Updating existing menu for {matched_canteen.name} ({meal_type})")
            existing_menu.original_text = text
            existing_menu.image_path = url
            existing_menu.courses_json = courses_json
            await menu_repo.update(existing_menu)
        else:
            logger.info(f"➕ Creating new menu for {matched_canteen.name} ({meal_type})")
            new_menu = Menu(
                canteen_id=matched_canteen.id,
                date=today,
                meal_type=meal_type,
                courses_json=courses_json,
                original_text=text,
                translated_text="",  # Empty - translation happens on-demand
                image_path=url,
                story_id=f"web_{int(datetime.now().timestamp())}"
            )
            await menu_repo.create(new_menu)
            
        logger.info(f"✅ Menu saved successfully")
        return "success"

    except Exception as e:
        logger.error(f"❌ Error processing URL: {e}", exc_info=True)
        return "error"


def _download_and_ocr_sync(url: str) -> Tuple[Optional[str], bool]:
    """
    Synchronous helper for downloading and OCR with improved preprocessing.
    
    Returns:
        Tuple of (extracted_text, is_valid_menu)
    """
    import hashlib
    
    url_hash = hashlib.md5(url.encode()).hexdigest()
    filename = f"story_{url_hash}.jpg"
    path = os.path.join(DOWNLOAD_DIR, filename)

    # 1. Download image if not cached
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
    else:
        logger.debug(f"♻️ Using cached image")

    # 2. Enhanced OCR extraction with multiple strategies
    try:
        image = cv2.imread(path)
        if image is None:
            logger.error(f"❌ Failed to read image: {path}")
            try:
                os.remove(path)
                logger.debug(f"🗑️ Removed corrupted image: {path}")
            except:
                pass
            return None, False

        # Try multiple OCR preprocessing strategies
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh1 = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(thresh1, lang='ita', config='--psm 6').strip()
        
        
        logger.debug(f"📝 OCR extracted {len(text)} characters")
        
        # 3. Validate menu with flexible keyword matching
        text_upper = text.upper()
        menu_keywords = [
            "MENSA UNIVERSITARIA",
            "MENU",
            "MENÙ",
            "UNIVERSITY CANTEEN"
        ]
        print(text_upper)
        is_valid_menu = any(keyword in text_upper for keyword in menu_keywords)
        
        if is_valid_menu:
            logger.debug(f"✅ Valid menu detected")
        else:
            logger.debug(f"⚠️ Not a valid menu (missing keywords)")
            os.remove(path)
        
        return text, is_valid_menu
        
    except Exception as e:
        logger.error(f"❌ OCR error: {e}", exc_info=True)
        return None, False


if __name__ == "__main__":
    try:
        asyncio.run(fetch_and_store_menus())
    except KeyboardInterrupt:
        logger.info("🛑 Stopped by user")