"""
Modello Subscription per gestione iscrizioni utente-mensa
"""
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint
from datetime import datetime
from models.base import BaseModel


class SubscriptionBase(SQLModel):
    """Schema base Subscription"""
    user_id: int = Field(foreign_key="users.id")
    canteen_id: int = Field(foreign_key="canteens.id") 
    is_active: bool = Field(default=True)
    meal_types: List[str] = Field(default_factory=lambda: ["lunch", "dinner"])
    notification_time_offset: int = Field(default=0)  # Minuti di offset rispetto all'orario standard


class Subscription(SubscriptionBase, BaseModel, table=True):
    """Modello Subscription per database"""
    __tablename__ = "subscriptions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Relationships
    user: "User" = Relationship(back_populates="subscriptions")
    canteen: "Canteen" = Relationship(back_populates="subscriptions")
    
    # Constraint unico per user+canteen
    __table_args__ = (
        UniqueConstraint("user_id", "canteen_id", name="unique_user_canteen_subscription"),
    )


class SubscriptionCreate(SubscriptionBase):
    """Schema per creazione Subscription"""
    pass


class SubscriptionUpdate(SQLModel):
    """Schema per aggiornamento Subscription"""
    is_active: Optional[bool] = None
    meal_types: Optional[List[str]] = None
    notification_time_offset: Optional[int] = None


class SubscriptionRead(SubscriptionBase):
    """Schema per lettura Subscription"""
    id: int
    created_at: datetime
    updated_at: datetime