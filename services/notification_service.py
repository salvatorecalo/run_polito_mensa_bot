"""
Notification Service: Sends menus from Database to Telegram Subscribers
"""

import asyncio
from datetime import datetime
from utils.decorator import inject_db
from utils.translate_text import translate_text
from utils.logger import setup_logger
# Ensure correct imports based on previous files
from database.connection import get_session
from database.models import Menu
from database.repositories import CanteenRepository, MenuRepository, UserRepository
from services.telegram_service import TelegramService
from utils.today import get_today_date
from telegram import Update
from telegram.ext import ContextTypes
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
        current_hour = datetime.now().hour
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
                caption = self._format_menu_caption(menu, canteen_name)
                # IL PROBLEMA STA QUI
                image_path = menu.image_path
                for user in canteen_users:
                    try:
                        # Send message (asynchronous Telegram API calls)
                        if image_path:
                            if user.image_or_text == "image":
                                await self.telegram.send_photo(
                                    chat_id=user.telegram_id,
                                    photo_path=image_path,
                                    caption=caption,
                                )
                            else:
                                await self.telegram.send_message(
                                    chat_id=user.telegram_id, text=caption
                                )
                    except Exception as e:
                        # Log error but continue with next user (don't break the loop)
                        logger.error(
                            f"❌ Failed to send to user {user.telegram_id}: {e}"
                        )

        logger.info("✅ Notification cycle completed.")

    def _format_menu_caption(self, menu: Menu, canteen_name: str) -> str:
        """Formats the menu into a readable Telegram message"""
        text = f"🍽️ *{canteen_name}*\n"
        text += (
            f"📅 {menu.date.strftime('%d/%m/%Y')} - {menu.meal_type.capitalize()}\n\n"
        )


            # Fallback to JSON
        courses = menu.courses_json
        if isinstance(courses, dict):
            for dishes in courses.values():

                if isinstance(dishes, list):
                    for dish in dishes:
                        text += f"{dish}\n"
                elif isinstance(dishes, str):
                    text += f"{dishes}\n"

                text += "\n"

        # Add footer
        text += "\n_Buon appetito! 😋_"
        return text
