"""
Database layer with SQLModel and Repository Pattern
"""

from database.connection import (
    close_db,
    create_db_and_tables,
    get_session,
    get_session_maker,
    init_db,
)
from database.models import Canteen, Menu, User
from database.repositories import (
    CanteenRepository,
    MenuRepository,
    UserRepository,
)

__all__ = [
    # Connection
    "init_db",
    "create_db_and_tables",
    "get_session",
    "get_session_maker",
    "close_db",
    # Models
    "Canteen",
    "Menu",
    "User",
    # Repositories
    "CanteenRepository",
    "MenuRepository",
    "UserRepository",
]
