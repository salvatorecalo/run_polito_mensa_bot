"""
Notification Service: Sends menus from Database to Telegram Subscribers
"""

import asyncio
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from utils.logger import setup_logger
from database.connection import get_session
from database.models import Menu
from database.repositories import CanteenRepository, MenuRepository, UserRepository
from services.telegram_service import TelegramService
from utils.today import get_today_date
from utils.translate_text import translate_text
logger = setup_logger(__name__)


class NotificationService:
    def __init__(self):
        # Assuming TelegramService is initialized properly with the token internally
        self.telegram = TelegramService()

    async def send_daily_menu(self) -> None:
        """
        Checks for today's menu in the DB and sends it to subscribers.
        """
        logger.info("📤 Starting daily menu notification...")

        # Determine meal type (Lunch < 15:00 <= Dinner)
        current_hour = datetime.now(ZoneInfo("Europe/Rome")).hour
        meal_type = "lunch" if current_hour < 15 else "dinner"

        async for session in get_session():
            user_repo = UserRepository(session)
            menu_repo = MenuRepository(session)
            canteen_repo = CanteenRepository(session)
            canteens = await canteen_repo.get_all()
            users_by_canteen = {}
            for canteen in canteens:
                if not canteen.id:
                    continue
                users = await user_repo.get_users_by_canteen(canteen.id)
                users_by_canteen[canteen.id] = users
            
            # 4. Process each canteen
            for canteen_id, canteen_users in users_by_canteen.items():
                # Fetch menu for this canteen
                menu = await menu_repo.get_menu_by_date(get_today_date(), canteen_id, meal_type)
                
                if not menu:
                    logger.info(f"ℹ️ No {meal_type} menu found for canteen {canteen_id}")
                    continue

                logger.info(
                    f"🚀 Sending {meal_type} menu to {len(canteen_users)} users (Canteen {canteen_id})"
                )

                # Get readable name
                canteen = await canteen_repo.get_by_id(canteen_id)
                if not canteen:
                    logger.info("No canteen found")
                    return
                if not canteen.name:
                    logger.info("No canteen name found")
                canteen_name = canteen.name
                
                for user in canteen_users:
                    if not user.is_active:
                        continue
                    
                    # Get user language
                    language = user.language if user.language else "it"
                    
                    # Format caption with user's language
                    caption = await self._format_menu_caption(menu, canteen_name, language)
                    
                    # Get image path for user's language
                    image_paths = menu.courses_json.get("image_paths", {}) if menu.courses_json else {}
                    target_image_path = image_paths.get(language, menu.image_path)
                    
                    try:
                        # Send message (asynchronous Telegram API calls)
                        if target_image_path and os.path.exists(target_image_path):
                            if user.image_or_text == "image":
                                await self.telegram.send_photo(
                                    chat_id=user.telegram_id,
                                    photo_path=target_image_path,
                                    caption=caption,
                                )
                            else:
                                await self.telegram.send_message(
                                    chat_id=user.telegram_id, text=caption
                                )
                        else:
                            # Fallback to text if image doesn't exist
                            await self.telegram.send_message(
                                chat_id=user.telegram_id, text=caption
                            )
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        if "403" in str(e) or "Forbidden" in str(e):
                            logger.warning(f"🚫 L'utente {user.telegram_id} ha bloccato il bot. Lo disattivo nel DB.")
                            await user_repo.update_status(user.telegram_id, is_active=False)
                        # Log error but continue with next user (don't break the loop)
                        logger.error(
                            f"❌ Failed to send to user {user.telegram_id}: {e}"
                        )

        logger.info("✅ Notification cycle completed.")

    async def _format_menu_caption(self, menu: Menu, canteen_name: str, language: str = "it") -> str:
        """Formats the menu into a readable Telegram message, translated to user's language"""
        meal_type_translated = await translate_text(menu.meal_type.capitalize(), language)
        text = f"🍽️ *{canteen_name}*\n"
        text += (
            f"📅 {menu.date.strftime('%d/%m/%Y')} - {meal_type_translated}\n\n"
        )

        # Get menu content - prioritize original_text for proper translation
        menu_content = menu.original_text or "Menu vuoto"
        if language != "it":
            try:
                translated_content = await translate_text(menu_content, language)
                if translated_content:
                    menu_content = translated_content
            except Exception as e:
                logger.warning(f"Failed to translate menu content to {language}: {e}")
        
        text += menu_content
        text += "\n\n"

        # Add footer
        footer = await translate_text("Buon appetito! 😋", language)
        text += f"_{footer}_"
        return text
