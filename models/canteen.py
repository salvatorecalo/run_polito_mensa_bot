"""
Modello Canteen per gestione mense
"""
from __future__ import annotations
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, Text
from datetime import datetime
from models.base import BaseModel


class CanteenBase(SQLModel):
    """Schema base Canteen"""
    name: str = Field(max_length=100)
    slug: str = Field(unique=True, index=True, max_length=50)
    address: Optional[str] = Field(default=None, max_length=200)
    instagram_username: Optional[str] = Field(default=None, max_length=30)
    is_active: bool = Field(default=True)
    extra_data: Optional[str] = Field(default=None, sa_type=Text)  # JSON as text


class Canteen(CanteenBase, BaseModel, table=True):
    """Modello Canteen per database"""
    __tablename__ = "canteens"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    menus: List["Menu"] = Relationship(back_populates="canteen")
    subscriptions: List["Subscription"] = Relationship(back_populates="canteen")


class CanteenCreate(CanteenBase):
    """Schema per creazione Canteen"""
    pass


class CanteenUpdate(SQLModel):
    """Schema per aggiornamento Canteen"""
    name: Optional[str] = None
    address: Optional[str] = None
    instagram_username: Optional[str] = None
    is_active: Optional[bool] = None
    extra_data: Optional[str] = None  # JSON as text


class CanteenRead(CanteenBase):
    """Schema per lettura Canteen"""
    id: int
    created_at: datetime
    updated_at: datetime