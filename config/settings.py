"""
Configurazione settings con Pydantic Settings
"""
import os
from typing import Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Determina il percorso della root del progetto
ROOT_DIR = Path(__file__).parent.parent
ENV_FILE = ROOT_DIR / '.env'

# Carica variabili d'ambiente
load_dotenv(dotenv_path=ENV_FILE, override=True)


class Settings(BaseSettings):
    """Configurazione applicazione con Pydantic Settings"""
    
    # Debug mode
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://polito_mensa:polito_mensa_password@localhost:5432/polito_mensa", 
        description="Database connection URL"
    )
    
    # Instagram credentials (backward compatibility)
    ig_username: str = Field(default="", alias="IG_USERNAME", description="Instagram username")
    ig_password: str = Field(default="", alias="IG_PASSWORD", description="Instagram password")
    instagram_username: str = Field(default="", description="Instagram username (alternative)")
    instagram_password: str = Field(default="", description="Instagram password (alternative)")
    target_user: str = Field(
        default="spotted_polito", 
        alias="TARGET_USER", 
        description="Instagram target user"
    )
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    
    # Telegram bot configuration  
    telegram_token: str = Field(default="", alias="BOT_TOKEN", description="Telegram bot token")
    telegram_chat_id: int = Field(default=0, alias="TELEGRAM_CHAT_ID", description="Admin chat ID")
    
    # Modern Database URLs
    database_url_sync: str = Field(
        default="postgresql://polito_mensa:polito_mensa_password@localhost:5432/polito_mensa",
        alias="DATABASE_URL_SYNC",
        description="Synchronous database URL for Alembic"
    )
    
    # File paths (backward compatibility)
    session_file: str = Field(
        default="data/ig_session.json", 
        alias="SESSION_FILE",
        description="Instagram session file"
    )
    subscribers_file: str = Field(
        default="data/subscribers.json", 
        alias="SUBSCRIBERS_FILE",
        description="Subscribers backup file"
    )
    
    # Directory paths
    download_dir: str = Field(default="download/stories", description="Stories download directory")
    created_images_dir: str = Field(default="download/created_images", description="Created images directory")
    
    # Retry configuration
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Log format"
    )
    
    # Redis (for Celery)
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL for Celery")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        populate_by_name = True  # Pydantic V2: replaces allow_population_by_field_name
        extra = "ignore"  # Ignora campi extra dall'environment


# Istanza globale
settings = Settings()

# Backward compatibility - export old constants
IG_USERNAME = settings.ig_username
IG_PASSWORD = settings.ig_password
TARGET_USER = settings.target_user
SESSION_FILE = settings.session_file
TELEGRAM_TOKEN = settings.telegram_token
TELEGRAM_CHAT_ID = settings.telegram_chat_id
SUBSCRIBERS_FILE = settings.subscribers_file
DOWNLOAD_DIR = settings.download_dir
CREATED_IMAGES_DIR = settings.created_images_dir
MAX_RETRIES = settings.max_retries
ROOT_DIR = ROOT_DIR