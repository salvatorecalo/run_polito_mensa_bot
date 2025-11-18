"""
Repository per gestione Menu
"""
from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from loguru import logger
from models.menu import Menu, MenuCreate, MenuUpdate, MenuStatus, MealType
from repositories.base import BaseRepository


class MenuRepository(BaseRepository[Menu, MenuCreate, MenuUpdate]):
    """Repository per operazioni su Menu"""
    
    def __init__(self):
        super().__init__(Menu)
    
    async def get_by_canteen_date_meal(
        self,
        session: AsyncSession,
        canteen_id: int,
        date: date,
        meal_type: MealType
    ) -> Optional[Menu]:
        """Ottieni menu specifico per mensa/data/pasto"""
        result = await session.execute(
            select(Menu).where(
                Menu.canteen_id == canteen_id,
                Menu.date == date,
                Menu.meal_type == meal_type
            )
        )
        return result.scalar_one_or_none()
    
    async def get_or_create_menu(
        self,
        session: AsyncSession,
        canteen_id: int,
        date: date,
        meal_type: MealType,
        raw_text: str,
        **menu_data
    ) -> tuple[Menu, bool]:
        """Ottieni menu o crealo se non esiste. Restituisce (menu, created)"""
        menu = await self.get_by_canteen_date_meal(session, canteen_id, date, meal_type)
        
        if menu:
            return menu, False
        
        # Crea nuovo menu
        menu_create = MenuCreate(
            canteen_id=canteen_id,
            date=date,
            meal_type=meal_type,
            raw_text=raw_text,
            **menu_data
        )
        menu = await self.create(session, menu_create)
        
        logger.info(f"📝 Nuovo menu creato per {canteen_id} - {date} - {meal_type}")
        return menu, True
    
    async def get_pending_menus(self, session: AsyncSession, limit: int = 50) -> List[Menu]:
        """Ottieni menu in attesa di elaborazione"""
        result = await session.execute(
            select(Menu)
            .where(Menu.status == MenuStatus.PENDING)
            .order_by(Menu.created_at)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_ready_for_sending(
        self, 
        session: AsyncSession,
        meal_type: MealType,
        target_date: date = None
    ) -> List[Menu]:
        """Ottieni menu pronti per l'invio"""
        if target_date is None:
            target_date = date.today()
        
        result = await session.execute(
            select(Menu)
            .where(
                Menu.date == target_date,
                Menu.meal_type == meal_type,
                Menu.status == MenuStatus.PROCESSED,
                Menu.sent_at.is_(None)
            )
        )
        return result.scalars().all()
    
    async def mark_as_sent(
        self, 
        session: AsyncSession, 
        menu_id: int
    ) -> Optional[Menu]:
        """Marca menu come inviato"""
        menu = await self.get(session, menu_id)
        if not menu:
            return None
        
        menu.status = MenuStatus.SENT
        menu.sent_at = datetime.utcnow()
        await session.commit()
        await session.refresh(menu)
        
        logger.info(f"📤 Menu {menu_id} marcato come inviato")
        return menu
    
    async def mark_as_processed(
        self,
        session: AsyncSession,
        menu_id: int,
        translated_text: str = None,
        parsed_items: List[str] = None
    ) -> Optional[Menu]:
        """Marca menu come elaborato"""
        menu = await self.get(session, menu_id)
        if not menu:
            return None
        
        menu.status = MenuStatus.PROCESSED
        if translated_text:
            menu.translated_text = translated_text
        if parsed_items:
            menu.parsed_items = parsed_items
        
        await session.commit()
        await session.refresh(menu)
        
        logger.info(f"✅ Menu {menu_id} marcato come elaborato")
        return menu
    
    async def mark_as_error(
        self,
        session: AsyncSession,
        menu_id: int,
        error_details: dict = None
    ) -> Optional[Menu]:
        """Marca menu come errore"""
        menu = await self.get(session, menu_id)
        if not menu:
            return None
        
        menu.status = MenuStatus.ERROR
        menu.processing_attempts += 1
        
        if error_details:
            metadata = menu.metadata or {}
            metadata["last_error"] = error_details
            menu.metadata = metadata
        
        await session.commit()
        await session.refresh(menu)
        
        logger.error(f"❌ Menu {menu_id} marcato come errore (attempt {menu.processing_attempts})")
        return menu
    
    async def get_menus_by_date_range(
        self,
        session: AsyncSession,
        start_date: date,
        end_date: date,
        canteen_id: int = None,
        meal_type: MealType = None
    ) -> List[Menu]:
        """Ottieni menu in un range di date"""
        query = select(Menu).where(
            Menu.date >= start_date,
            Menu.date <= end_date
        )
        
        if canteen_id:
            query = query.where(Menu.canteen_id == canteen_id)
        
        if meal_type:
            query = query.where(Menu.meal_type == meal_type)
        
        result = await session.execute(query.order_by(Menu.date, Menu.meal_type))
        return result.scalars().all()


# Istanza globale
menu_repository = MenuRepository()