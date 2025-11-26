"""
Scraper Service for fetching menus from Instagram and storing them in the Database.
Can be run as a standalone script or scheduled task.
"""

import asyncio
import os
from typing import Optional, Tuple

import cv2
import googletrans
import pytesseract
import requests
from instagrapi.types import Story

from config import DOWNLOAD_DIR, TARGET_USER
from database.connection import create_db_and_tables, get_session, init_db
from database.models import Canteen, Menu
from database.repositories import CanteenRepository, MenuRepository
from services.instagram_service import InstagramService
from utils.logger import setup_logger

logger = setup_logger(__name__)


async def fetch_and_store_menus() -> None:
    """
    Main entry point: Fetches stories, processes them, and upserts into the DB.
    """
    logger.info("🚀 Starting Scraper Service...")

    # 1. Initialize Database
    await init_db()
    await create_db_and_tables()

    # 2. Login to Instagram
    ig_service = InstagramService()

    # Execute blocking calls in a separate thread
    try:

        def fetch_stories_sync():
            client = ig_service.login()
            user_id = client.user_id_from_username(TARGET_USER)  # type: ignore
            logger.info(f"👤 Target User: {TARGET_USER} (ID: {user_id})")
            return client.user_stories(user_id)

        # Execute blocking calls in a separate thread
        stories = await asyncio.to_thread(fetch_stories_sync)
        logger.info(f"📸 Found {len(stories)} stories")

    except Exception as e:
        logger.error(f"❌ Failed to fetch stories from Instagram: {e}")
        return

    if not stories:
        logger.info("⚠️ No stories available.")
        return

    # 3. Process and Store
    async for session in get_session():
        canteen_repo = CanteenRepository(session)
        menu_repo = MenuRepository(session)

        # Ensure Canteen exists
        canteen = await canteen_repo.get_by_name(TARGET_USER)
        if not canteen:
            logger.info(f"🆕 Creating new canteen: {TARGET_USER}")
            canteen = await canteen_repo.create(
                Canteen(
                    name=TARGET_USER, location_description="Imported from Instagram"
                )
            )

        # Use Translator
        # Note: googletrans==4.0.0-rc1 supports async context manager
        async with googletrans.Translator() as translator:
            for story in stories:
                if canteen.id is None:
                    continue

                await _process_single_story(story, canteen, menu_repo, translator)

    logger.info("✅ Scraper Service completed.")


async def _process_single_story(
    story: Story,
    canteen: Canteen,
    menu_repo: MenuRepository,
    translator: googletrans.Translator,
) -> None:
    """
    Process a single story: Download -> OCR -> Translate -> Upsert DB
    """
    # Skip if not an image (media_type 1 = Photo)
    if story.media_type != 1:
        return

    # --- 1. Download & OCR (CPU/IO Bound - Run in Thread) ---
    try:
        text, image_path = await asyncio.to_thread(
            _download_and_ocr_sync, story, canteen.name
        )
    except Exception as e:
        logger.error(f"❌ Error processing image for story {story.id}: {e}")
        return

    if not text or len(text) < 10:
        logger.debug(f"⏭️ Skipping story {story.id}: Text too short or empty")
        return

    # --- 2. Translation (Async) ---
    try:
        # Googletrans async API
        translated = await translator.translate(text, dest="en")
        translated_text = translated.text
    except Exception as e:
        logger.warning(f"⚠️ Translation failed: {e}")
        translated_text = "Translation unavailable"

    # --- 3. Determine Metadata ---
    # story.taken_at is UTC datetime
    story_date = story.taken_at.date()

    # Heuristic: < 14:00 UTC is Lunch, else Dinner
    meal_type = "lunch" if story.taken_at.hour < 14 else "dinner"

    courses_json = {
        "raw_lines": [line for line in text.split("\n") if line.strip()],
        "meta": {"source": "instagram", "story_id": story.id},
    }

    # --- 4. Upsert Logic ---
    if canteen.id is None:
        return

    existing_menu = await menu_repo.get_menu_by_date(story_date, canteen.id, meal_type)

    if existing_menu:
        # Update if story ID changed (new version of same menu)
        if existing_menu.story_id != str(story.id):
            logger.info(f"🔄 Updating menu {story_date} ({meal_type})")
            existing_menu.original_text = text
            existing_menu.translated_text = translated_text
            existing_menu.image_path = image_path
            existing_menu.story_id = str(story.id)
            existing_menu.courses_json = courses_json
            await menu_repo.update(existing_menu)
    else:
        logger.info(f"➕ Creating menu {story_date} ({meal_type})")
        new_menu = Menu(
            canteen_id=canteen.id,
            date=story_date,
            meal_type=meal_type,
            courses_json=courses_json,
            original_text=text,
            translated_text=translated_text,
            image_path=image_path,
            story_id=str(story.id),
        )
        await menu_repo.create(new_menu)


def _download_and_ocr_sync(
    story: Story, canteen_name: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Synchronous helper for downloading and OCR.
    Executed in a separate thread to avoid blocking the async event loop.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    filename = f"{canteen_name}_{story.id}.jpg"
    path = os.path.join(DOWNLOAD_DIR, filename)

    # 1. Download
    if not os.path.exists(path):
        if not story.thumbnail_url:
            return None, None

        try:
            # Use requests (blocking) safely here because we are in a thread
            response = requests.get(str(story.thumbnail_url), timeout=30)
            response.raise_for_status()
            with open(path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None, None

    # 2. OCR
    try:
        image = cv2.imread(path)
        if image is None:
            return None, None

        # Preprocessing for better OCR
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Apply thresholding to binaraize image (optional but often helps)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        text = pytesseract.image_to_string(thresh).strip()
        return text, path
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return None, None


if __name__ == "__main__":
    try:
        asyncio.run(fetch_and_store_menus())
    except KeyboardInterrupt:
        pass
