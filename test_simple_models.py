"""
Test semplice per verificare i modelli
"""
from sqlmodel import SQLModel, Field
from typing import Optional
import json


class SimpleUser(SQLModel, table=True):
    """Modello User semplificato per test"""
    __tablename__ = "users_test"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(unique=True, index=True)
    username: Optional[str] = Field(default=None, max_length=32)
    first_name: Optional[str] = Field(default=None, max_length=64)
    is_active: bool = Field(default=True)


if __name__ == "__main__":
    try:
        user = SimpleUser(chat_id=123, username="test")
        print(f"✅ Simple user created: {user}")
        print("✅ Simple models work correctly")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()