"""
Database models using SQLModel (Pydantic + SQLAlchemy)
"""

from datetime import date as date_type
from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    """Helper to get current UTC time with timezone info"""
    return datetime.now(timezone.utc)


class Canteen(SQLModel, table=True):
    """
    Canteen entity - Represents a university cafeteria

    Example:
        canteen = Canteen(
            name="Mensa Centrale",
            location_description="Via Cavalli, 22 - Torino"
        )
    """

    __tablename__: ClassVar[str] = "canteens"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=100)
    location_description: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    
    # Use timezone-aware datetime
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Menu(SQLModel, table=True):
    """
    Menu entity - Stores daily menus for canteens

    The 'courses_json' field stores flexible menu data:
    {
        "primi": ["Pasta al pomodoro", "Risotto ai funghi"],
        "secondi": ["Pollo arrosto", "Pesce al forno"],
        "contorni": ["Insalata", "Patate"],
        "dolci": ["Tiramisù"]
    }
    """

    __tablename__: ClassVar[str] = "menus"

    id: Optional[int] = Field(default=None, primary_key=True)
    canteen_id: int = Field(foreign_key="canteens.id", index=True)
    date: date_type = Field(index=True)
    meal_type: str = Field(max_length=20)  # "lunch" or "dinner"

    # JSON field for flexible menu structure
    # Using sa_column=Column(JSON) ensures proper handling in PostgreSQL
    courses_json: dict[str, Any] = Field(sa_column=Column(JSON))

    # Full text fields for reference
    original_text: str  # Original OCR text (Italian)
    translated_text: str  # Translated text (English)

    # Image reference
    image_path: Optional[str] = Field(default=None, max_length=255)
    story_id: Optional[str] = Field(default=None, unique=True, max_length=100)

    created_at: datetime = Field(default_factory=utc_now)


class User(SQLModel, table=True):
    """
    User entity - Telegram users subscribed to the bot
    """

    __tablename__: ClassVar[str] = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True, index=True)
    first_name: str = Field(max_length=100)
    username: Optional[str] = Field(default=None, max_length=100)

    # User preferences
    selected_canteen_id: Optional[int] = Field(default=None, foreign_key="canteens.id")
    is_active: bool = Field(default=True)
    language: str = Field(default="en", max_length=5)  # "en" or "it"

    subscribed_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)