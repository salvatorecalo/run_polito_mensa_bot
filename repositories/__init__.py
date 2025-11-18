"""
Init file per repositories
"""
from repositories.base import BaseRepository
from repositories.user import UserRepository, user_repository
from repositories.canteen import CanteenRepository, canteen_repository
from repositories.menu import MenuRepository, menu_repository
from repositories.subscription import SubscriptionRepository, subscription_repository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "user_repository",
    "CanteenRepository", 
    "canteen_repository",
    "MenuRepository",
    "menu_repository",
    "SubscriptionRepository",
    "subscription_repository",
]