"""
Scraper Service for fetching menus from Instagram and storing them in the Database.
Can be run as a standalone script or scheduled task.
"""

import asyncio
import logging
import os
from datetime import datetime

import cv2
import googletrans
import pytesseract
import requests
from instagrapi.types import Story

from config import DOWNLOAD_DIR, TARGET_USER
from database.connection import get_session, init_db
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

    # 2. Login to Instagram
    ig_service = InstagramService()
    try:
        cl = ig_service.login()
    except Exception as e:
        logger.error(f"❌ Instagram login failed: {e}")
        return

    # 3. Fetch Stories
    try:
        # Resolve User ID
        if not TARGET_USER:
            logger.error("❌ TARGET_USER is not configured")
            return
        user_info = cl.user_info_by_username(TARGET_USER)
        user_id = user_info.pk
        logger.info(f"👤 Target User: {TARGET_USER} (ID: {user_id})")

        # Get Stories
        stories = cl.user_stories(user_id)
        logger.info(f"📸 Found {len(stories)} stories")
    except Exception as e:
        logger.error(f"❌ Failed to fetch stories: {e}")
        return

    if not stories:
        logger.info("⚠️ No stories available.")
        return

    # 4. Process and Store
    async for session in get_session():
        canteen_repo = CanteenRepository(session)
        menu_repo = MenuRepository(session)

        # Ensure Canteen exists (Upsert logic for Canteen)
        canteen = await canteen_repo.get_by_name(TARGET_USER)
        if not canteen:
            logger.info(f"🆕 Creating new canteen: {TARGET_USER}")
            canteen = await canteen_repo.create(
                Canteen(
                    name=TARGET_USER, location_description="Imported from Instagram"
                )
            )

        # Use Translator context manager
        async with googletrans.Translator() as translator:
            for story in stories:
                if canteen.id is None:
                    logger.error("❌ Canteen ID is None, cannot process stories")
                    return
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

    # --- 1. Download Image ---
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    filename = f"{canteen.name}_{story.id}.jpg"
    path = os.path.join(DOWNLOAD_DIR, filename)

    if not os.path.exists(path):
        if not story.thumbnail_url:
            logger.error(f"❌ No thumbnail URL for story {story.id}")
            return
        try:
            response = requests.get(str(story.thumbnail_url), timeout=30)
            response.raise_for_status()
            with open(path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            logger.error(f"❌ Download failed for story {story.id}: {e}")
            return

    # --- 2. OCR Extraction ---
    try:
        image = cv2.imread(path)
        if image is None:
            return
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        text = pytesseract.image_to_string(gray).strip()
    except Exception as e:
        logger.error(f"❌ OCR failed: {e}")
        return

    if len(text) < 10:
        logger.debug(f"⏭️ Skipping story {story.id}: Text too short")
        return

    # --- 3. Translation ---
    try:
        translated = await translator.translate(text, dest="en")
        translated_text = translated.text
    except Exception as e:
        logger.error(f"❌ Translation failed: {e}")
        translated_text = "Translation unavailable"

    # --- 4. Determine Metadata ---
    # story.taken_at is usually UTC.
    story_date = story.taken_at.date()

    # Simple heuristic for meal type based on hour (UTC)
    # If posted before 14:00 UTC, assume Lunch, else Dinner
    meal_type = "lunch" if story.taken_at.hour < 14 else "dinner"

    # Prepare JSON structure
    courses_json = {
        "raw_lines": [line for line in text.split("\n") if line.strip()],
        "meta": {"source": "instagram", "story_id": story.id},
    }

    # --- 5. Upsert Logic ---
    # Check if a menu already exists for this date/canteen/meal
    if canteen.id is None:
        logger.error("❌ Canteen ID is None, cannot check existing menu")
        return
    existing_menu = await menu_repo.get_menu_by_date(story_date, canteen.id, meal_type)

    if existing_menu:
        # Update if it's a new story or we want to refresh data
        # (Here we update if the story ID is different, implying a newer update)
        if existing_menu.story_id != str(story.id):
            logger.info(f"🔄 Updating menu {story_date} ({meal_type})")
            existing_menu.original_text = text
            existing_menu.translated_text = translated_text
            existing_menu.image_path = path
            existing_menu.story_id = str(story.id)
            existing_menu.courses_json = courses_json
            await menu_repo.update(existing_menu)
        else:
            logger.debug(f"✅ Menu {story_date} ({meal_type}) already up to date")
    else:
        if canteen.id is None:
            logger.error("❌ Canteen ID is None, cannot create menu")
            return
        logger.info(f"➕ Creating menu {story_date} ({meal_type})")
        new_menu = Menu(
            canteen_id=canteen.id,
            date=story_date,
            meal_type=meal_type,
            courses_json=courses_json,
            original_text=text,
            translated_text=translated_text,
            image_path=path,
            story_id=str(story.id),
        )
        await menu_repo.create(new_menu)


if __name__ == "__main__":
    # Run standalone
    try:
        asyncio.run(fetch_and_store_menus())
    except KeyboardInterrupt:
        pass
