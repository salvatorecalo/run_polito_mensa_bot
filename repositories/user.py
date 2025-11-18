"""
Repository per gestione Users
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from loguru import logger
from models.user import User, UserCreate, UserUpdate
from repositories.base import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Repository per operazioni su User"""
    
    def __init__(self):
        super().__init__(User)
    
    async def get_by_chat_id(self, session: AsyncSession, chat_id: int) -> Optional[User]:
        """Ottieni user per chat_id Telegram"""
        result = await session.execute(select(User).where(User.chat_id == chat_id))
        return result.scalar_one_or_none()
    
    async def get_or_create_by_chat_id(
        self, 
        session: AsyncSession, 
        chat_id: int, 
        **user_data
    ) -> User:
        """Ottieni user per chat_id o crealo se non esiste"""
        user = await self.get_by_chat_id(session, chat_id)
        
        if not user:
            user_create = UserCreate(chat_id=chat_id, **user_data)
            user = await self.create(session, user_create)
            logger.info(f"👤 Nuovo utente creato: {chat_id} ({user.first_name})")
        
        return user
    
    async def get_active_users(self, session: AsyncSession) -> List[User]:
        """Ottieni tutti gli utenti attivi"""
        result = await session.execute(select(User).where(User.is_active == True))
        return result.scalars().all()
    
    async def deactivate_user(self, session: AsyncSession, chat_id: int) -> bool:
        """Disattiva un utente per chat_id"""
        user = await self.get_by_chat_id(session, chat_id)
        if not user:
            return False
        
        user.is_active = False
        await session.commit()
        
        logger.info(f"🔒 Utente disattivato: {chat_id}")
        return True
    
    async def activate_user(self, session: AsyncSession, chat_id: int) -> bool:
        """Riattiva un utente per chat_id"""
        user = await self.get_by_chat_id(session, chat_id)
        if not user:
            return False
        
        user.is_active = True
        await session.commit()
        
        logger.info(f"✅ Utente riattivato: {chat_id}")
        return True
    
    async def update_preferences(
        self, 
        session: AsyncSession, 
        chat_id: int, 
        preferences: dict
    ) -> Optional[User]:
        """Aggiorna preferenze utente"""
        user = await self.get_by_chat_id(session, chat_id)
        if not user:
            return None
        
        # Merge delle preferenze esistenti
        current_prefs = user.preferences or {}
        updated_prefs = {**current_prefs, **preferences}
        user.preferences = updated_prefs
        
        await session.commit()
        await session.refresh(user)
        
        logger.debug(f"🔧 Preferenze aggiornate per utente {chat_id}")
        return user
    
    async def get_users_by_language(
        self, 
        session: AsyncSession, 
        language_code: str
    ) -> List[User]:
        """Ottieni utenti per lingua"""
        result = await session.execute(
            select(User).where(
                User.language_code == language_code,
                User.is_active == True
            )
        )
        return result.scalars().all()


# Istanza globale
user_repository = UserRepository()