"""
Modelli base del database con SQLModel
"""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from pydantic import ConfigDict


class TimestampMixin(SQLModel):
    """Mixin per timestamp automatici"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BaseModel(TimestampMixin):
    """Modello base con configurazione comune"""
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )