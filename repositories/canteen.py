"""
Repository per gestione Canteen
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from loguru import logger
from models.canteen import Canteen, CanteenCreate, CanteenUpdate
from repositories.base import BaseRepository


class CanteenRepository(BaseRepository[Canteen, CanteenCreate, CanteenUpdate]):
    """Repository per operazioni su Canteen"""
    
    def __init__(self):
        super().__init__(Canteen)
    
    async def get_by_slug(self, session: AsyncSession, slug: str) -> Optional[Canteen]:
        """Ottieni mensa per slug"""
        result = await session.execute(select(Canteen).where(Canteen.slug == slug))
        return result.scalar_one_or_none()
    
    async def get_by_instagram_username(
        self, 
        session: AsyncSession, 
        instagram_username: str
    ) -> Optional[Canteen]:
        """Ottieni mensa per username Instagram"""
        result = await session.execute(
            select(Canteen).where(Canteen.instagram_username == instagram_username)
        )
        return result.scalar_one_or_none()
    
    async def get_active_canteens(self, session: AsyncSession) -> List[Canteen]:
        """Ottieni tutte le mense attive"""
        result = await session.execute(select(Canteen).where(Canteen.is_active == True))
        return result.scalars().all()
    
    async def get_canteens_with_instagram(self, session: AsyncSession) -> List[Canteen]:
        """Ottieni mense con account Instagram configurato"""
        result = await session.execute(
            select(Canteen).where(
                Canteen.is_active == True,
                Canteen.instagram_username.isnot(None)
            )
        )
        return result.scalars().all()
    
    async def deactivate_canteen(self, session: AsyncSession, canteen_id: int) -> bool:
        """Disattiva una mensa"""
        canteen = await self.get(session, canteen_id)
        if not canteen:
            return False
        
        canteen.is_active = False
        await session.commit()
        
        logger.info(f"🔒 Mensa {canteen.name} disattivata")
        return True
    
    async def activate_canteen(self, session: AsyncSession, canteen_id: int) -> bool:
        """Riattiva una mensa"""
        canteen = await self.get(session, canteen_id)
        if not canteen:
            return False
        
        canteen.is_active = True
        await session.commit()
        
        logger.info(f"✅ Mensa {canteen.name} riattivata")
        return True
    
    async def update_metadata(
        self,
        session: AsyncSession,
        canteen_id: int,
        metadata: dict
    ) -> Optional[Canteen]:
        """Aggiorna metadata mensa"""
        canteen = await self.get(session, canteen_id)
        if not canteen:
            return None
        
        # Merge dei metadata esistenti
        current_metadata = canteen.metadata or {}
        updated_metadata = {**current_metadata, **metadata}
        canteen.metadata = updated_metadata
        
        await session.commit()
        await session.refresh(canteen)
        
        logger.debug(f"🔧 Metadata aggiornati per mensa {canteen.name}")
        return canteen


# Istanza globale
canteen_repository = CanteenRepository()