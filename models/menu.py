"""
Modello Menu per gestione menu giornalieri
"""
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint, Text
from models.base import BaseModel


class MealType(str, Enum):
    """Tipo di pasto"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch" 
    DINNER = "dinner"
    SNACK = "snack"


class MenuStatus(str, Enum):
    """Status del menu"""
    PENDING = "pending"      # In attesa di elaborazione
    PROCESSED = "processed"  # Elaborato con successo
    SENT = "sent"           # Inviato agli utenti
    ERROR = "error"         # Errore durante elaborazione


class MenuBase(SQLModel):
    """Schema base Menu"""
    canteen_id: int = Field(foreign_key="canteens.id")
    date: date = Field(index=True)
    meal_type: MealType = Field(index=True)
    
    # Contenuto originale
    raw_text: str = Field(max_length=2000)
    original_image_url: Optional[str] = Field(default=None, max_length=500)
    
    # Contenuto elaborato  
    parsed_items: Optional[str] = Field(default=None, sa_type=Text)  # JSON as text
    translated_text: Optional[str] = Field(default=None, max_length=2000)
    
    # Status e metadata
    status: MenuStatus = Field(default=MenuStatus.PENDING, index=True)
    processing_attempts: int = Field(default=0)
    sent_at: Optional[datetime] = Field(default=None)
    extra_data: Optional[str] = Field(default=None, sa_type=Text)  # JSON as text


class Menu(MenuBase, BaseModel, table=True):
    """Modello Menu per database"""
    __tablename__ = "menus"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    canteen: "Canteen" = Relationship(back_populates="menus")
    
    # Constraint unico per canteen+date+meal_type
    __table_args__ = (
        UniqueConstraint("canteen_id", "date", "meal_type", name="unique_menu_per_meal"),
    )


class MenuCreate(MenuBase):
    """Schema per creazione Menu"""
    pass


class MenuUpdate(SQLModel):
    """Schema per aggiornamento Menu"""
    raw_text: Optional[str] = None
    translated_text: Optional[str] = None
    parsed_items: Optional[str] = None  # JSON as text
    status: Optional[MenuStatus] = None
    processing_attempts: Optional[int] = None
    sent_at: Optional[datetime] = None
    extra_data: Optional[str] = None  # JSON as text


class MenuRead(MenuBase):
    """Schema per lettura Menu"""
    id: int
    created_at: datetime
    updated_at: datetime