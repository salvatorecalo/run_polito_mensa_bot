from database.connection import get_session_maker
from database.repositories import UserRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)

async def set_admins(telegram_ids):
    Session = get_session_maker()
    session = Session()
    try:
        user_repo = UserRepository(session)
        for tid in telegram_ids:
            user = await user_repo.get_by_telegram_id(tid)
            if user:
                user.is_admin = True
                print(f"✅ Utente {user.first_name} ({tid}) impostato come admin")
        await session.commit()
    finally:
        await session.close()

