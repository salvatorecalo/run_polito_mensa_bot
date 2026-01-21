"""
Notification Service: Sends menus from Database to Telegram Subscribers
"""

from datetime import datetime
from utils.logger import setup_logger
# Ensure correct imports based on previous files
from database.connection import get_session
from database.models import Menu
from database.repositories import CanteenRepository, MenuRepository, UserRepository
from services.telegram_service import TelegramService
from utils.today import get_today_date

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

            # 1. Fetch Canteens first to map ID -> Name (UX improvement)
            canteens = await canteen_repo.get_all()
            canteen_map = {c.id: c.name for c in canteens}

            # 2. Get all active users
            users = await user_repo.get_all_active()
            if not users:
                logger.info("⚠️ No active subscribers found.")
                return

            # 3. Group users by canteen to minimize DB queries
            #    Structure: {canteen_id: [user_list]}
            users_by_canteen = {}
            for user in users:
                if user.selected_canteen_ids:
                    if user.selected_canteen_ids not in users_by_canteen:
                        users_by_canteen[user.selected_canteen_ids] = []
                    users_by_canteen[user.selected_canteen_ids].append(user)

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
                canteen_name = canteen_map.get(canteen_id, f"Canteen {canteen_id}")

                # Prepare message content
                caption = self._format_menu_caption(menu, canteen_name)
                image_path = menu.image_path

                # Send to each user
                for user in canteen_users:
                    try:
                        # Send message (asynchronous Telegram API calls)
                        if image_path:
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
            for course, dishes in courses.items():
                # Format header (e.g., "PRIMI")
                text += f"*{course.upper()}*:\n"

                if isinstance(dishes, list):
                    for dish in dishes:
                        text += f"- {dish}\n"
                elif isinstance(dishes, str):
                    text += f"- {dishes}\n"

                text += "\n"

        # Add footer
        text += "\n_Buon appetito! 😋_"
        return text
