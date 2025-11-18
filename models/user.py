"""
Modello User per gestione iscritti Telegram
"""
from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, Text
from datetime import datetime
from models.base import BaseModel


class UserBase(SQLModel):
    """Schema base User"""
    chat_id: int = Field(unique=True, index=True)
    username: Optional[str] = Field(default=None, max_length=32)
    first_name: Optional[str] = Field(default=None, max_length=64)
    last_name: Optional[str] = Field(default=None, max_length=64)
    language_code: Optional[str] = Field(default="it", max_length=8)
    is_active: bool = Field(default=True)
    is_bot: bool = Field(default=False)
    preferences: Optional[str] = Field(default=None, sa_type=Text)  # JSON as text


class User(UserBase, BaseModel, table=True):
    """Modello User per database"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    subscriptions: List["Subscription"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    """Schema per creazione User"""
    pass


class UserUpdate(SQLModel):
    """Schema per aggiornamento User"""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_active: Optional[bool] = None
    preferences: Optional[str] = None  # JSON as text


class UserRead(UserBase):
    """Schema per lettura User"""
    id: int
    created_at: datetime
    updated_at: datetime