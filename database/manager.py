"""
Configurazione database con SQLModel + AsyncPG
"""
import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from loguru import logger
from config.settings import settings


class DatabaseManager:
    """Manager per gestione database asincrono"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.async_session: Optional[sessionmaker] = None
        self._initialize()
    
    def _initialize(self):
        """Inizializza engine e sessionmaker"""
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1 ora
            pool_size=20,
            max_overflow=0,
        )
        
        self.async_session = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def create_tables(self) -> None:
        """Crea tutte le tabelle"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
            
        async with self.engine.begin() as conn:
            # Import dei modelli per assicurare che siano registrati
            from models import User, Canteen, Menu, Subscription
            await conn.run_sync(SQLModel.metadata.create_all)
        
        logger.info("✅ Tabelle database create")
    
    async def drop_tables(self) -> None:
        """Elimina tutte le tabelle (solo per testing)"""
        if not self.engine:
            raise RuntimeError("Database engine not initialized")
            
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        
        logger.warning("🗑️ Tabelle database eliminate")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Genera una sessione database asincrona"""
        if not self.async_session:
            raise RuntimeError("Session factory not initialized")
            
        async with self.async_session() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self) -> None:
        """Chiude il database engine"""
        if self.engine:
            await self.engine.dispose()
            logger.info("🔒 Database engine chiuso")
    
    async def health_check(self) -> bool:
        """Verifica la connessione al database"""
        try:
            async for session in self.get_session():
                result = await session.execute(select(1))
                result.scalar_one()
                return True
        except Exception as e:
            logger.error(f"❌ Database health check failed: {e}")
            return False


# Istanza globale
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection per handlers"""
    async for session in db_manager.get_session():
        yield session


async def init_database() -> None:
    """Inizializza database e popolazione dati iniziali"""
    await db_manager.create_tables()
    
    # Popola dati iniziali
    async for session in db_manager.get_session():
        await populate_initial_data(session)
        await session.commit()


async def populate_initial_data(session: AsyncSession) -> None:
    """Popola dati iniziali (mense, ecc.)"""
    from models.canteen import Canteen
    
    # Verifica se già esistono mense
    existing = await session.execute(select(Canteen))
    if existing.first():
        logger.info("🏠 Mense già esistenti, skip popolazione")
        return
    
    # Crea mense Politecnico
    canteens = [
        Canteen(
            name="Mensa Politecnico - Cittadella",
            slug="polito-cittadella", 
            address="Cittadella Politecnica, Torino",
            instagram_username="spotted_polito",
            is_active=True,
            metadata={"type": "university", "capacity": 500, "website": "https://polito.it"}
        ),
        Canteen(
            name="Mensa EDISU - Palazzo Nuovo",
            slug="edisu-palazzo-nuovo",
            address="Via Verdi 8, Torino", 
            instagram_username="edisu_piemonte",
            is_active=True,
            metadata={"type": "edisu", "capacity": 300, "website": "https://edisu.piemonte.it"}
        ),
    ]
    
    for canteen in canteens:
        session.add(canteen)
    
    logger.info(f"🏠 Aggiunte {len(canteens)} mense iniziali")


# Event handlers per gestione connessioni
async def startup_db():
    """Avvio database"""
    logger.info("🚀 Avvio connessione database")
    await init_database()
    
    # Health check
    if await db_manager.health_check():
        logger.info("✅ Database connesso e funzionante")
    else:
        logger.error("❌ Errore connessione database")


async def shutdown_db():
    """Chiusura database"""
    logger.info("🔒 Chiusura connessione database")
    await db_manager.close()