"""
Repository pattern implementation for data access
Provides clean abstraction between business logic and database
"""

from datetime import date, datetime
from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, col
from utils.logger import setup_logger
from database.models import Canteen, Menu, User
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

ModelType = TypeVar("ModelType", bound=SQLModel)

logger = setup_logger(__name__)

class BaseRepository(Generic[ModelType]):
    """
    Generic base repository with common CRUD operations

    Usage:
        class MyRepository(BaseRepository[MyModel]):
            pass
    """

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Get entity by primary key

        Args:
            id: Primary key value

        Returns:
            Entity instance or None
        """
        return await self.session.get(self.model, id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get all entities with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of entities
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        """
        Create new entity

        Args:
            obj: Entity instance to create

        Returns:
            Created entity with ID
        """
        try:
            self.session.add(obj)
            await self.session.commit()
            await self.session.refresh(obj)
            return obj
        except IntegrityError as e:
            await self.session.rollback()
            logger.error(f"❌ Integrity error creating {self.model.__name__}: {e}")
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"❌ Database error creating {self.model.__name__}: {e}")
            raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Unexpected error creating {self.model.__name__}: {e}")
            raise

    async def update(self, obj: ModelType) -> ModelType:
        """
        Update existing entity

        Args:
            obj: Entity instance to update

        Returns:
            Updated entity
        """
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: int) -> bool:
        """
        Delete entity by ID

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """
        obj = await self.get_by_id(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            return True
        return False


class CanteenRepository(BaseRepository[Canteen]):
    """
    Repository for Canteen entities

    Example:
        async for session in get_session():
            repo = CanteenRepository(session)
            canteen = await repo.get_by_name("Mensa Centrale")
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Canteen)

    async def get_by_name(self, name: str) -> Optional[Canteen]:
        """
        Find canteen by exact name

        Args:
            name: Canteen name

        Returns:
            Canteen or None
        """
        # Wrapped in col() to ensure Pylance treats it as a Column, not a str
        stmt = select(Canteen).where(col(Canteen.name).ilike(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[Canteen]:
        """
        Get all active canteens

        Returns:
            List of active canteens
        """
        # Wrapped in col() to avoid 'bool' assignment errors
        stmt = select(Canteen).where(col(Canteen.is_active) == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_location(self, location: str) -> List[Canteen]:
        """
        Search canteens by location description (case-insensitive)

        Args:
            location: Partial location text

        Returns:
            List of matching canteens
        """
        # Wrapped in col() to access .ilike(), which str class does not have
        stmt = select(Canteen).where(
            col(Canteen.location_description).ilike(f"%{location}%")
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    
    async def seed_default_canteens(self) -> List[Canteen]:
        """
        Create default test canteens if they don't exist

        Returns:
            List of created/existing canteens
        """
        default_canteens_data = [
            {
                "name": "Mensa Centrale",
                "location_description": "Torino, Campus Luigi Einaudi",
                "is_active": True
            },
            {
                "name": "Mensa Palazzo Nuovo",
                "location_description": "Torino, Via Sant'Ottavio 20",
                "is_active": True
            },
            {
                "name": "Mensa Biotecnologie",
                "location_description": "Torino, Via Nizza 52",
                "is_active": True
            }
        ]
        
        created_canteens = []
        
        for canteen_data in default_canteens_data:
            # Check if already exists
            existing = await self.get_by_name(canteen_data["name"])
            
            if not existing:
                # Create new canteen
                canteen = Canteen(**canteen_data)
                created = await self.create(canteen)
                created_canteens.append(created)
            else:
                created_canteens.append(existing)
        
        return created_canteens


class MenuRepository(BaseRepository[Menu]):
    """
    Repository for Menu entities

    Example:
        async for session in get_session():
            repo = MenuRepository(session)
            menu = await repo.get_menu_by_date(date.today(), canteen_id=1)
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Menu)

    async def get_menu_by_date(
        self, target_date: date, canteen_id: int, meal_type: str = "lunch"
    ) -> Optional[Menu]:
        """
        Get menu for specific date, canteen, and meal type

        Args:
            target_date: Date of the menu
            canteen_id: ID of the canteen
            meal_type: "lunch" or "dinner"

        Returns:
            Menu or None if not found
        """
        stmt = select(Menu).where(
            col(Menu.date) == target_date,
            col(Menu.canteen_id) == canteen_id,
            col(Menu.meal_type) == meal_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_menus_by_date_for_canteens(
        self, target_date: date, canteen_ids: List[int], meal_type: str = "lunch"
    ) -> List[Menu]:
        """
        Get menus for multiple canteens on a specific date

        Args:
            target_date: Date of the menu
            canteen_ids: List of canteen IDs
            meal_type: "lunch" or "dinner"

        Returns:
            List of menus
        """
        stmt = select(Menu).where(
            col(Menu.date) == target_date,
            col(Menu.canteen_id).in_(canteen_ids),
            col(Menu.meal_type) == meal_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_menus_by_date_range(
        self, start_date: date, end_date: date, canteen_id: Optional[int] = None
    ) -> List[Menu]:
        """
        Get all menus within a date range

        Args:
            start_date: Start date
            end_date: End date
            canteen_id: Optional canteen filter

        Returns:
            List of menus
        """
        stmt = select(Menu).where(
            col(Menu.date) >= start_date, col(Menu.date) <= end_date
        )

        if canteen_id:
            stmt = stmt.where(col(Menu.canteen_id) == canteen_id)

        # Used sqlalchemy.desc() function instead of .desc() method
        # Also wrapped columns in col()
        stmt = stmt.order_by(desc(col(Menu.date)), Menu.meal_type)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_menu(self, canteen_id: int) -> Optional[Menu]:
        """
        Get the most recent menu for a canteen

        Args:
            canteen_id: ID of the canteen

        Returns:
            Latest menu or None
        """
        stmt = (
            select(Menu)
            .where(col(Menu.canteen_id) == canteen_id)
            .order_by(desc(col(Menu.date)), desc(col(Menu.created_at)))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def menu_exists(
        self, target_date: date, canteen_id: int, meal_type: str
    ) -> bool:
        """
        Check if menu already exists

        Args:
            target_date: Date to check
            canteen_id: Canteen ID
            meal_type: Meal type

        Returns:
            True if exists, False otherwise
        """
        menu = await self.get_menu_by_date(target_date, canteen_id, meal_type)
        return menu is not None


class UserRepository(BaseRepository[User]):
    """
    Repository for User entities

    Example:
        async for session in get_session():
            repo = UserRepository(session)
            user = await repo.get_by_telegram_id(123456789)
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Find user by Telegram ID

        Args:
            telegram_id: Telegram user ID

        Returns:
            User or None
        """
        stmt = select(User).where(col(User.telegram_id) == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self, telegram_id: int, first_name: str, username: Optional[str] = None
    ) -> User:
        """
        Get existing user or create new one

        Args:
            telegram_id: Telegram user ID
            first_name: User's first name
            username: Optional username

        Returns:
            User instance
        """
        user = await self.get_by_telegram_id(telegram_id)

        if user:
            # Update user info if changed
            if user.first_name != first_name or user.username != username:
                user.first_name = first_name
                user.username = username
                user.updated_at = datetime.utcnow()
                await self.session.commit()
                await self.session.refresh(user)
            return user

        # Create new user
        user = User(telegram_id=telegram_id, first_name=first_name, username=username)
        return await self.create(user)

    async def get_all_active(self) -> List[User]:
        """
        Get all active users

        Returns:
            List of active users
        """
        stmt = select(User).where(col(User.is_active) == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_users_by_canteen(self, canteen_id: int) -> List[User]:
        """
        Get all users subscribed to a specific canteen

        Args:
            canteen_id: Canteen ID

        Returns:
            List of users
        """
        stmt = (
            select(User)
            .where(col(User.is_active) == True)  # noqa: E712
        )
        result = await self.session.execute(stmt)
        users =  list(result.scalars().all())
        return [user for user in users if canteen_id in user.selected_canteen_ids]

    async def add_canteen_to_user(
        self, telegram_id: int, canteen_id: int
    ) -> bool:
        """
        Add a canteen to user's subscriptions

        Args:
            telegram_id: Telegram user ID
            canteen_id: Canteen ID to add

        Returns:
            True if added, False if user not found or already subscribed
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return False

        # Controlla se già iscritto
        if canteen_id in user.selected_canteen_ids:
            return False

        user.selected_canteen_ids = user.selected_canteen_ids + [canteen_id]
        user.updated_at = datetime.now()
        await self.session.commit()
        await self.session.refresh(user)
        return True

    async def remove_canteen_from_user(
        self, telegram_id: int, canteen_id: int
    ) -> bool:
        """
        Remove a canteen from user's subscriptions

        Args:
            telegram_id: Telegram user ID
            canteen_id: Canteen ID to remove

        Returns:
            True if removed, False if user not found or not subscribed
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return False

        # Controlla se è iscritto
        if canteen_id not in user.selected_canteen_ids:
            return False

        user.selected_canteen_ids = [
            cid for cid in user.selected_canteen_ids if cid != canteen_id
        ]
        user.updated_at = datetime.now()
        await self.session.commit()
        await self.session.refresh(user)
        return True

    async def is_user_subscribed_to_canteen(
        self, telegram_id: int, canteen_id: int
    ) -> bool:
        """
        Check if user is subscribed to a specific canteen

        Args:
            telegram_id: Telegram user ID
            canteen_id: Canteen ID

        Returns:
            True if subscribed, False otherwise
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return False
        return canteen_id in user.selected_canteen_ids

    async def get_user_canteens(self, telegram_id: int) -> List[int]:
        """
        Get list of canteen IDs user is subscribed to

        Args:
            telegram_id: Telegram user ID

        Returns:
            List of canteen IDs
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return []
        return user.selected_canteen_ids

    
    async def update_status(self, telegram_id: int, is_active: bool) -> bool:
        """
        Activate or deactivate user

        Args:
            telegram_id: Telegram user ID
            is_active: New status

        Returns:
            True if updated, False if user not found
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return False
        user.is_active = is_active
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        # Corrected indentation here
        return True
    
    async def update_user_language(self, telegram_id: int, new_language: str) -> bool:
        """
        Set user bot language

        Args:
            telegram_id: Telegram user ID
            new_language: new language of the bot
        
        Returns:
            True if updated, False if user not found
        """
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return False
        user.language = new_language
        await self.session.commit()
        return True