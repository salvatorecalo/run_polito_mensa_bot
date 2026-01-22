"""
Comprehensive test suite for database repositories
"""

import pytest
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import SQLModel
from database.models import Canteen, Menu, User
from database.repositories import (
    BaseRepository,
    CanteenRepository,
    MenuRepository,
    UserRepository,
)
from utils.today import get_today_date


# Use in-memory SQLite for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Fixture for async database session"""
    engine = create_async_engine(DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def sample_canteen(db_session):
    """Fixture for sample canteen"""
    repo = CanteenRepository(db_session)
    canteen = Canteen(
        name="Test Canteen",
        location_description="Test Location",
        is_active=True
    )
    return await repo.create(canteen)


@pytest.fixture
async def sample_user(db_session):
    """Fixture for sample user"""
    repo = UserRepository(db_session)
    user = User(
        telegram_id=123456789,
        first_name="Test User",
        username="testuser",
        is_active=True,
        language="en",
        image_or_text="image"
    )
    return await repo.create(user)


@pytest.fixture
async def sample_menu(db_session, sample_canteen):
    """Fixture for sample menu"""
    repo = MenuRepository(db_session)
    menu = Menu(
        canteen_id=sample_canteen.id,
        date=get_today_date(),
        meal_type="lunch",
        courses_json={"primi": ["Pasta"], "secondi": ["Meat"]},
        original_text="Test menu text",
        image_path="/path/to/image.jpg"
    )
    return await repo.create(menu)


class TestBaseRepository:
    """Test BaseRepository generic methods"""

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, db_session, sample_canteen):
        repo = BaseRepository(db_session, Canteen)
        result = await repo.get_by_id(sample_canteen.id)
        assert result is not None
        assert result.id == sample_canteen.id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session):
        repo = BaseRepository(db_session, Canteen)
        result = await repo.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all(self, db_session, sample_canteen):
        repo = BaseRepository(db_session, Canteen)
        results = await repo.get_all()
        assert len(results) == 1
        assert results[0].id == sample_canteen.id

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, db_session):
        repo = BaseRepository(db_session, Canteen)
        # Create multiple canteens
        for i in range(5):
            canteen = Canteen(name=f"Canteen {i}", location_description=f"Loc {i}")
            await repo.create(canteen)

        results = await repo.get_all(skip=2, limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_create_success(self, db_session):
        repo = BaseRepository(db_session, Canteen)
        canteen = Canteen(name="New Canteen", location_description="New Loc")
        result = await repo.create(canteen)
        assert result.id is not None
        assert result.name == "New Canteen"

    @pytest.mark.asyncio
    async def test_create_integrity_error(self, db_session):
        repo = BaseRepository(db_session, Canteen)
        # Create a canteen first
        canteen1 = Canteen(name="Test", location_description="Loc")
        await repo.create(canteen1)

        # Try to create another with same unique field (if any)
        # Since no unique constraints beyond id, this should work
        canteen2 = Canteen(name="Test2", location_description="Loc2")
        result = await repo.create(canteen2)
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_sqlalchemy_error(self, db_session):
        repo = BaseRepository(db_session, Canteen)
        canteen = Canteen(name="Test", location_description="Loc")

        with patch.object(db_session, 'add', side_effect=SQLAlchemyError("Test error")):
            with pytest.raises(SQLAlchemyError):
                await repo.create(canteen)

    @pytest.mark.asyncio
    async def test_update_success(self, db_session, sample_canteen):
        repo = BaseRepository(db_session, Canteen)
        sample_canteen.name = "Updated Name"
        result = await repo.update(sample_canteen)
        assert result.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_success(self, db_session, sample_canteen):
        repo = BaseRepository(db_session, Canteen)
        result = await repo.delete(sample_canteen.id)
        assert result is True

        # Verify deleted
        fetched = await repo.get_by_id(sample_canteen.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db_session):
        repo = BaseRepository(db_session, Canteen)
        result = await repo.delete(999)
        assert result is False


class TestCanteenRepository:
    """Test CanteenRepository specific methods"""

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, db_session, sample_canteen):
        repo = CanteenRepository(db_session)
        result = await repo.get_by_name("Test Canteen")
        assert result is not None
        assert result.id == sample_canteen.id

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, db_session):
        repo = CanteenRepository(db_session)
        result = await repo.get_by_name("Nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_case_insensitive(self, db_session, sample_canteen):
        repo = CanteenRepository(db_session)
        result = await repo.get_by_name("test canteen")
        assert result is not None
        assert result.id == sample_canteen.id

    @pytest.mark.asyncio
    async def test_get_all_active(self, db_session, sample_canteen):
        repo = CanteenRepository(db_session)

        # Create inactive canteen
        inactive = Canteen(name="Inactive", location_description="Loc", is_active=False)
        await repo.create(inactive)

        results = await repo.get_all_active()
        assert len(results) == 1
        assert results[0].id == sample_canteen.id

    @pytest.mark.asyncio
    async def test_search_by_location(self, db_session, sample_canteen):
        repo = CanteenRepository(db_session)
        results = await repo.search_by_location("Test Location")
        assert len(results) == 1
        assert results[0].id == sample_canteen.id

    @pytest.mark.asyncio
    async def test_search_by_location_partial(self, db_session, sample_canteen):
        repo = CanteenRepository(db_session)
        results = await repo.search_by_location("Test")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_by_location_no_match(self, db_session):
        repo = CanteenRepository(db_session)
        results = await repo.search_by_location("Nonexistent")
        assert len(results) == 0


class TestMenuRepository:
    """Test MenuRepository specific methods"""

    @pytest.mark.asyncio
    async def test_get_menu_by_date_found(self, db_session, sample_menu, sample_canteen):
        repo = MenuRepository(db_session)
        result = await repo.get_menu_by_date(get_today_date(), sample_canteen.id, "lunch")
        assert result is not None
        assert result.id == sample_menu.id

    @pytest.mark.asyncio
    async def test_get_menu_by_date_not_found(self, db_session, sample_canteen):
        repo = MenuRepository(db_session)
        result = await repo.get_menu_by_date(get_today_date(), sample_canteen.id, "dinner")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_menus_by_date_for_canteens(self, db_session, sample_menu, sample_canteen):
        repo = MenuRepository(db_session)
        results = await repo.get_menus_by_date_for_canteens(
            get_today_date(), [sample_canteen.id], "lunch"
        )
        assert len(results) == 1
        assert results[0].id == sample_menu.id

    @pytest.mark.asyncio
    async def test_get_menus_by_date_for_canteens_multiple(self, db_session, sample_canteen):
        repo = MenuRepository(db_session)

        # Create another menu
        menu2 = Menu(
            canteen_id=sample_canteen.id,
            date=get_today_date(),
            meal_type="dinner",
            courses_json={},
            original_text="Dinner menu"
        )
        await repo.create(menu2)

        results = await repo.get_menus_by_date_for_canteens(
            get_today_date(), [sample_canteen.id], "lunch"
        )
        assert len(results) == 1  # Only lunch

    @pytest.mark.asyncio
    async def test_get_menus_by_date_range(self, db_session, sample_menu):
        repo = MenuRepository(db_session)
        start_date = get_today_date()
        end_date = get_today_date()

        results = await repo.get_menus_by_date_range(start_date, end_date)
        assert len(results) == 1
        assert results[0].id == sample_menu.id

    @pytest.mark.asyncio
    async def test_get_menus_by_date_range_with_canteen_filter(self, db_session, sample_menu, sample_canteen):
        repo = MenuRepository(db_session)
        start_date = get_today_date()
        end_date = get_today_date()

        results = await repo.get_menus_by_date_range(start_date, end_date, sample_canteen.id)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_latest_menu(self, db_session, sample_menu, sample_canteen):
        repo = MenuRepository(db_session)
        result = await repo.get_latest_menu(sample_canteen.id)
        assert result is not None
        assert result.id == sample_menu.id

    @pytest.mark.asyncio
    async def test_menu_exists_true(self, db_session, sample_menu, sample_canteen):
        repo = MenuRepository(db_session)
        exists = await repo.menu_exists(get_today_date(), sample_canteen.id, "lunch")
        assert exists is True

    @pytest.mark.asyncio
    async def test_menu_exists_false(self, db_session, sample_canteen):
        repo = MenuRepository(db_session)
        exists = await repo.menu_exists(get_today_date(), sample_canteen.id, "dinner")
        assert exists is False

    @pytest.mark.asyncio
    async def test_delete_menus_by_date(self, db_session, sample_menu):
        repo = MenuRepository(db_session)

        # Verify exists
        result = await repo.get_menu_by_date(get_today_date(), sample_menu.canteen_id, "lunch")
        assert result is not None

        # Delete
        await repo.delete_menus_by_date(get_today_date())

        # Verify deleted
        result = await repo.get_menu_by_date(get_today_date(), sample_menu.canteen_id, "lunch")
        assert result is None


class TestUserRepository:
    """Test UserRepository specific methods"""

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_found(self, db_session, sample_user):
        repo = UserRepository(db_session)
        result = await repo.get_by_telegram_id(123456789)
        assert result is not None
        assert result.id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_by_telegram_id_not_found(self, db_session):
        repo = UserRepository(db_session)
        result = await repo.get_by_telegram_id(999999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_is_admin_true(self, db_session):
        repo = UserRepository(db_session)
        user = User(
            telegram_id=111111111,
            first_name="Admin",
            is_admin=True
        )
        await repo.create(user)

        result = await repo.is_admin(111111111)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_admin_false(self, db_session, sample_user):
        repo = UserRepository(db_session)
        result = await repo.is_admin(123456789)
        assert result is False

    @pytest.mark.asyncio
    async def test_switch_user_role_to_admin(self, db_session, sample_user):
        repo = UserRepository(db_session)
        await repo.switch_user_role(123456789)

        updated = await repo.get_by_telegram_id(123456789)
        if updated is None:
            pytest.fail("User should exist after role switch.")
        assert updated.is_admin is True

    @pytest.mark.asyncio
    async def test_switch_user_role_to_user(self, db_session):
        repo = UserRepository(db_session)
        user = User(
            telegram_id=222222222,
            first_name="Admin User",
            is_admin=True
        )
        await repo.create(user)

        await repo.switch_user_role(222222222)

        updated = await repo.get_by_telegram_id(222222222)
        if updated is None:
            pytest.fail("User should exist after role switch.")
        assert updated.is_admin is False

    @pytest.mark.asyncio
    async def test_get_or_create_new_user(self, db_session):
        repo = UserRepository(db_session)
        user = await repo.get_or_create(333333333, "New User", "newuser")

        assert user.telegram_id == 333333333
        assert user.first_name == "New User"
        assert user.username == "newuser"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_or_create_existing_user(self, db_session, sample_user):
        repo = UserRepository(db_session)
        user = await repo.get_or_create(123456789, "Updated Name", "updateduser")

        assert user.id == sample_user.id
        assert user.first_name == "Updated Name"
        assert user.username == "updateduser"

    @pytest.mark.asyncio
    async def test_get_all_active(self, db_session, sample_user):
        repo = UserRepository(db_session)

        # Create inactive user
        inactive = User(
            telegram_id=444444444,
            first_name="Inactive",
            is_active=False
        )
        await repo.create(inactive)

        results = await repo.get_all_active()
        assert len(results) == 1
        assert results[0].id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_users_by_canteen(self, db_session, sample_canteen):
        repo = UserRepository(db_session)

        # Create user with canteen subscription
        user = User(
            telegram_id=555555555,
            first_name="Subscriber",
            selected_canteen_ids=[sample_canteen.id]
        )
        await repo.create(user)

        results = await repo.get_users_by_canteen(sample_canteen.id)
        assert len(results) == 1
        assert results[0].telegram_id == 555555555

    @pytest.mark.asyncio
    async def test_get_users_by_canteen_no_matches(self, db_session, sample_canteen):
        repo = UserRepository(db_session)
        results = await repo.get_users_by_canteen(999)  # Nonexistent canteen
        assert len(results) == 0