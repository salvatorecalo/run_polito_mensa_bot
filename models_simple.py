"""
Modelli database semplificati per SQLModel
Senza relationships circolari - versione temporanea per testing
"""
from datetime import date as Date, datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field, Text


class MealType(str, Enum):
    """Tipo di pasto"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch" 
    DINNER = "dinner"
    SNACK = "snack"


class MenuStatus(str, Enum):
    """Status del menu"""
    PENDING = "pending"
    PROCESSED = "processed"
    SENT = "sent"
    ERROR = "error"


# === Base Models senza relationships ===

class User(SQLModel, table=True):
    """User model semplificato"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(unique=True, index=True)
    username: Optional[str] = Field(default=None, max_length=32)
    first_name: Optional[str] = Field(default=None, max_length=64)
    last_name: Optional[str] = Field(default=None, max_length=64)
    language_code: Optional[str] = Field(default="it", max_length=8)
    is_active: bool = Field(default=True)
    is_bot: bool = Field(default=False)
    preferences: Optional[str] = Field(default=None, sa_type=Text)  # JSON as TEXT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Canteen(SQLModel, table=True):
    """Canteen model semplificato"""
    __tablename__ = "canteens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    slug: str = Field(unique=True, index=True, max_length=50)
    address: Optional[str] = Field(default=None, max_length=200)
    instagram_username: Optional[str] = Field(default=None, max_length=30)
    is_active: bool = Field(default=True)
    extra_data: Optional[str] = Field(default=None, sa_type=Text)  # JSON as TEXT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Menu(SQLModel, table=True):
    """Menu model semplificato"""
    __tablename__ = "menus"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    canteen_id: int = Field(foreign_key="canteens.id", index=True)
    date: Date = Field(index=True)
    meal_type: MealType = Field(index=True)
    
    # Contenuto
    raw_text: str = Field(max_length=2000)
    original_image_url: Optional[str] = Field(default=None, max_length=500)
    parsed_items: Optional[str] = Field(default=None, sa_type=Text)  # JSON as TEXT
    translated_text: Optional[str] = Field(default=None, max_length=2000)
    
    # Status
    status: MenuStatus = Field(default=MenuStatus.PENDING, index=True)
    processing_attempts: int = Field(default=0)
    sent_at: Optional[datetime] = Field(default=None)
    extra_data: Optional[str] = Field(default=None, sa_type=Text)  # JSON as TEXT
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Subscription(SQLModel, table=True):
    """Subscription model semplificato"""
    __tablename__ = "subscriptions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    canteen_id: int = Field(foreign_key="canteens.id", index=True)
    meal_types: str = Field(default="LUNCH")  # Comma-separated values
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)