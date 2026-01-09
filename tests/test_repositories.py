import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
from database.models import Canteen, Menu
from database.repositories import UserRepository, CanteenRepository, MenuRepository
from utils import today
# Use in-memory SQLite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    # 1. Create the Async Engine
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)

    # 2. Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # 3. Use async_sessionmaker instead of sessionmaker
    # This correctly types the factory to return an AsyncSession and accept an AsyncEngine
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # 4. Yield the session
    async with async_session() as session:
        yield session

    # 5. Cleanup
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_repository(db_session):
    repo = UserRepository(db_session)

    # Create
    user = await repo.get_or_create(telegram_id=123, first_name="Test")
    assert user.telegram_id == 123
    assert user.first_name == "Test"

    # Get
    fetched = await repo.get_by_telegram_id(123)
    assert fetched is not None
    assert fetched.id == user.id

    # Update status
    await repo.update_status(123, False)
    fetched = await repo.get_by_telegram_id(123)
    assert fetched is not None
    assert fetched.is_active is False


@pytest.mark.asyncio
async def test_canteen_repository(db_session):
    repo = CanteenRepository(db_session)

    canteen = Canteen(name="Test Canteen", location_description="Loc")
    await repo.create(canteen)

    fetched = await repo.get_by_name("Test Canteen")
    assert fetched is not None
    assert fetched.location_description == "Loc"


@pytest.mark.asyncio
async def test_menu_repository(db_session):
    c_repo = CanteenRepository(db_session)
    canteen = await c_repo.create(Canteen(name="Mensa", location_description="Loc"))

    assert canteen.id is not None

    m_repo = MenuRepository(db_session)
    menu = Menu(
        canteen_id=canteen.id,
        date=today,
        meal_type="lunch",
        courses_json={},
        original_text="txt",
    )
    await m_repo.create(menu)

    fetched = await m_repo.get_menu_by_date(today, canteen.id, "lunch")
    assert fetched is not None
    assert fetched.original_text == "txt"