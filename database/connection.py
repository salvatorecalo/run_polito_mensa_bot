"""
Database connection and session management with async support
"""

from utils.logger import setup_logger
import os
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

logger = setup_logger(__name__)

# Global engine and session maker
# Type hints added to prevent "Variable is not defined" or "None" type errors
engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db(database_url: str | None = None) -> None:
    """
    Initialize database engine and session maker

    Args:
        database_url: Database connection URL (optional, uses env if not provided)
    """
    global engine, async_session_maker

    if database_url is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, "data", "bot.db")
        database_url = f"sqlite+aiosqlite:///{db_path}"

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
    # Removed 'autocommit=False' as it is deprecated in SQLAlchemy 2.0 style
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
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
    # noqa: F401 prevents linters from removing this unused import
    from database.models import Canteen, Menu, User  # noqa: F401

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

    session = async_session_maker()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_session_maker() -> async_sessionmaker[AsyncSession]:
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
