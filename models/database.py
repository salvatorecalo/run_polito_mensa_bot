"""
Database models using SQLModel
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Subscriber(SQLModel, table=True):
    """Subscriber database model"""

    __tablename__ = "subscribers"

    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(unique=True, index=True)
    username: Optional[str] = None
    is_active: bool = Field(default=True)
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Menu(SQLModel, table=True):
    """Menu database model"""

    __tablename__ = "menus"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime = Field(index=True)
    meal_type: str  # "lunch" or "dinner"
    restaurant_name: str
    original_text: str
    translated_text: str
    image_path: Optional[str] = None
    story_id: Optional[str] = Field(default=None, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
