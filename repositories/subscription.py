"""
Repository per gestione Subscription
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.orm import selectinload
from loguru import logger
from models.subscription import Subscription, SubscriptionCreate, SubscriptionUpdate
from models.user import User
from models.canteen import Canteen
from repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription, SubscriptionCreate, SubscriptionUpdate]):
    """Repository per operazioni su Subscription"""
    
    def __init__(self):
        super().__init__(Subscription)
    
    async def get_by_user_and_canteen(
        self,
        session: AsyncSession,
        user_id: int,
        canteen_id: int
    ) -> Optional[Subscription]:
        """Ottieni iscrizione per user e canteen"""
        result = await session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.canteen_id == canteen_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_chat_id_and_canteen_slug(
        self,
        session: AsyncSession,
        chat_id: int,
        canteen_slug: str
    ) -> Optional[Subscription]:
        """Ottieni iscrizione per chat_id e slug mensa"""
        result = await session.execute(
            select(Subscription)
            .join(User, Subscription.user_id == User.id)
            .join(Canteen, Subscription.canteen_id == Canteen.id)
            .where(
                User.chat_id == chat_id,
                Canteen.slug == canteen_slug
            )
            .options(
                selectinload(Subscription.user),
                selectinload(Subscription.canteen)
            )
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_subscription(
        self,
        session: AsyncSession,
        user_id: int,
        canteen_id: int,
        meal_types: List[str] = None,
        notification_time_offset: int = 0
    ) -> tuple[Subscription, bool]:
        """Crea o aggiorna iscrizione. Restituisce (subscription, created)"""
        subscription = await self.get_by_user_and_canteen(session, user_id, canteen_id)
        
        if subscription:
            # Aggiorna esistente
            subscription.is_active = True
            if meal_types is not None:
                subscription.meal_types = meal_types
            subscription.notification_time_offset = notification_time_offset
            
            await session.commit()
            await session.refresh(subscription)
            
            logger.info(f"🔄 Iscrizione aggiornata per user {user_id} - canteen {canteen_id}")
            return subscription, False
        else:
            # Crea nuova
            subscription_create = SubscriptionCreate(
                user_id=user_id,
                canteen_id=canteen_id,
                meal_types=meal_types or ["lunch", "dinner"],
                notification_time_offset=notification_time_offset
            )
            subscription = await self.create(session, subscription_create)
            
            logger.info(f"➕ Nuova iscrizione per user {user_id} - canteen {canteen_id}")
            return subscription, True
    
    async def deactivate_subscription(
        self,
        session: AsyncSession,
        user_id: int,
        canteen_id: int
    ) -> bool:
        """Disattiva iscrizione"""
        subscription = await self.get_by_user_and_canteen(session, user_id, canteen_id)
        if not subscription:
            return False
        
        subscription.is_active = False
        await session.commit()
        
        logger.info(f"🔒 Iscrizione disattivata per user {user_id} - canteen {canteen_id}")
        return True
    
    async def get_active_subscriptions_for_user(
        self,
        session: AsyncSession,
        user_id: int
    ) -> List[Subscription]:
        """Ottieni tutte le iscrizioni attive di un utente"""
        result = await session.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.is_active == True
            )
            .options(selectinload(Subscription.canteen))
        )
        return result.scalars().all()
    
    async def get_subscriptions_by_chat_id(
        self,
        session: AsyncSession,
        chat_id: int
    ) -> List[Subscription]:
        """Ottieni iscrizioni per chat_id Telegram"""
        result = await session.execute(
            select(Subscription)
            .join(User, Subscription.user_id == User.id)
            .where(
                User.chat_id == chat_id,
                Subscription.is_active == True
            )
            .options(
                selectinload(Subscription.user),
                selectinload(Subscription.canteen)
            )
        )
        return result.scalars().all()
    
    async def get_subscribers_for_canteen_and_meal(
        self,
        session: AsyncSession,
        canteen_id: int,
        meal_type: str
    ) -> List[Subscription]:
        """Ottieni tutti gli iscritti per una mensa e tipo pasto"""
        result = await session.execute(
            select(Subscription)
            .join(User, Subscription.user_id == User.id)
            .where(
                Subscription.canteen_id == canteen_id,
                Subscription.is_active == True,
                User.is_active == True,
                Subscription.meal_types.contains([meal_type])  # JSONContains per PostgreSQL
            )
            .options(
                selectinload(Subscription.user),
                selectinload(Subscription.canteen)
            )
        )
        return result.scalars().all()
    
    async def count_active_subscriptions(self, session: AsyncSession) -> int:
        """Conta le iscrizioni attive totali"""
        return await self.count(session, is_active=True)
    
    async def count_subscribers_per_canteen(
        self,
        session: AsyncSession,
        canteen_id: int
    ) -> int:
        """Conta gli iscritti per una mensa specifica"""
        return await self.count(session, canteen_id=canteen_id, is_active=True)


# Istanza globale
subscription_repository = SubscriptionRepository()