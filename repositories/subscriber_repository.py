"""
Subscriber repository - Data access layer
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import Subscriber
from utils.logger import setup_logger

logger = setup_logger(__name__)


class SubscriberRepository:
    """Repository for subscriber data access"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_chat_id(self, chat_id: int) -> Optional[Subscriber]:
        """Get subscriber by chat_id"""
        stmt = select(Subscriber).where(Subscriber.chat_id == chat_id)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[Subscriber]:
        """Get all active subscribers"""
        stmt = select(Subscriber).where(Subscriber.is_active == True)  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, chat_id: int, username: Optional[str] = None) -> Subscriber:
        """Create new subscriber"""
        subscriber = Subscriber(chat_id=chat_id, username=username, is_active=True)
        self.session.add(subscriber)
        await self.session.commit()
        await self.session.refresh(subscriber)

        logger.info(f"✅ Created subscriber: {chat_id}")
        return subscriber

    async def update_status(self, chat_id: int, is_active: bool) -> bool:
        """Update subscriber status"""
        subscriber = await self.get_by_chat_id(chat_id)
        if not subscriber:
            return False

        subscriber.is_active = is_active
        await self.session.commit()

        logger.info(f"✅ Updated subscriber {chat_id}: active={is_active}")
        return True

    async def get_all_chat_ids(self) -> List[int]:
        """Get all active subscriber chat IDs"""
        subscribers = await self.get_all_active()
        return [s.chat_id for s in subscribers]
