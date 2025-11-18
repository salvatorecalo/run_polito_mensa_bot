"""
Repository Pattern base per operazioni database
"""
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select
from pydantic import BaseModel
from loguru import logger

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Repository base con operazioni CRUD comuni"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, session: AsyncSession, id: int) -> Optional[ModelType]:
        """Ottieni record per ID"""
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_by_field(
        self, 
        session: AsyncSession, 
        field_name: str, 
        value: Any
    ) -> Optional[ModelType]:
        """Ottieni record per campo specifico"""
        field = getattr(self.model, field_name)
        result = await session.execute(select(self.model).where(field == value))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        **filters: Any
    ) -> List[ModelType]:
        """Ottieni multipli record con paginazione e filtri"""
        query = select(self.model)
        
        # Applica filtri
        for field_name, value in filters.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                query = query.where(field == value)
        
        query = query.offset(skip).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
    
    async def create(
        self, 
        session: AsyncSession, 
        obj_in: CreateSchemaType
    ) -> ModelType:
        """Crea nuovo record"""
        obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        db_obj = self.model(**obj_data)
        session.add(db_obj)
        await session.commit()
        await session.refresh(db_obj)
        
        logger.debug(f"Created {self.model.__name__} with id {db_obj.id}")
        return db_obj
    
    async def update(
        self,
        session: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType
    ) -> ModelType:
        """Aggiorna record esistente"""
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
        
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        
        await session.commit()
        await session.refresh(db_obj)
        
        logger.debug(f"Updated {self.model.__name__} with id {db_obj.id}")
        return db_obj
    
    async def delete(self, session: AsyncSession, id: int) -> bool:
        """Elimina record per ID"""
        obj = await self.get(session, id)
        if not obj:
            return False
        
        await session.delete(obj)
        await session.commit()
        
        logger.debug(f"Deleted {self.model.__name__} with id {id}")
        return True
    
    async def count(self, session: AsyncSession, **filters: Any) -> int:
        """Conta record con filtri opzionali"""
        from sqlalchemy import func
        
        query = select(func.count(self.model.id))
        
        # Applica filtri
        for field_name, value in filters.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                query = query.where(field == value)
        
        result = await session.execute(query)
        return result.scalar()
    
    async def exists(self, session: AsyncSession, **filters: Any) -> bool:
        """Verifica se esiste almeno un record con i filtri specificati"""
        count = await self.count(session, **filters)
        return count > 0