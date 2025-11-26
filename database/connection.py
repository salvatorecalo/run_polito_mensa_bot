"""
Database connection and session management with async support
"""

import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)

# Global engine and session maker
engine = None
async_session_maker = None


async def init_db(database_url: str | None = None) -> None:
    """
    Initialize database engine and session maker

    Args:
        database_url: Database connection URL (optional, uses env if not provided)
    """
    global engine, async_session_maker

    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/bot.db")

    logger.info(f"🗄️ Initializing database: {database_url}")

    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
        future=True,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Create session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    logger.info("✅ Database engine initialized")


async def create_db_and_tables() -> None:
    """
    Create database tables (idempotent - safe to call multiple times)
    """
    if engine is None:
        await init_db()

    if engine is None:
        raise RuntimeError("Failed to initialize database engine")

    # Import models to register them with SQLModel
    from database.models import Canteen, Menu, User

    logger.info("📋 Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("✅ Database tables ready")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection function to get database session

    Yields:
        AsyncSession instance

    Example:
        async for session in get_session():
            repo = MenuRepository(session)
            menu = await repo.get_menu_by_date(date.today(), canteen_id=1)
    """
    if async_session_maker is None:
        await init_db()

    if async_session_maker is None:
        raise RuntimeError("Failed to initialize database session maker")

    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_session_maker() -> async_sessionmaker:
    """
    Get the session maker for manual session creation

    Returns:
        async_sessionmaker instance
    """
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return async_session_maker


async def close_db() -> None:
    """
    Close database connections gracefully
    """
    global engine
    if engine:
        logger.info("🔒 Closing database connections...")
        await engine.dispose()
        engine = None
        logger.info("✅ Database closed")
