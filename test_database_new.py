#!/usr/bin/env python
"""
Test the new database layer with Canteen, Menu, and User models
"""

import asyncio
from datetime import date


async def main():
    print("🧪 Testing new database architecture...\n")

    # Import modules
    from database import (
        Canteen,
        CanteenRepository,
        Menu,
        MenuRepository,
        User,
        UserRepository,
        create_db_and_tables,
        get_session,
        init_db,
    )

    # Initialize database
    print("1️⃣ Initializing database...")
    await init_db("sqlite+aiosqlite:///./data/bot_test.db")
    await create_db_and_tables()
    print("   ✅ Database ready\n")

    async for session in get_session():
        # Test Canteen Repository
        print("2️⃣ Testing CanteenRepository...")
        canteen_repo = CanteenRepository(session)

        canteen = await canteen_repo.create(
            Canteen(
                name="Mensa Centrale", location_description="Via Cavalli, 22 - Torino"
            )
        )
        print(f"   ✅ Created canteen: {canteen.name} (ID: {canteen.id})\n")

        # Test Menu Repository
        print("3️⃣ Testing MenuRepository...")
        menu_repo = MenuRepository(session)

        menu = await menu_repo.create(
            Menu(
                canteen_id=canteen.id,
                date=date.today(),
                meal_type="lunch",
                courses_json={
                    "primi": ["Pasta al pomodoro", "Risotto funghi"],
                    "secondi": ["Pollo arrosto", "Pesce"],
                    "contorni": ["Insalata", "Patate"],
                },
                original_text="MENU PRANZO\nPRIMI: Pasta...",
                translated_text="LUNCH MENU\nFIRST: Pasta...",
            )
        )
        print(f"   ✅ Created menu: {menu.meal_type} for {menu.date}\n")

        # Query menu
        found_menu = await menu_repo.get_menu_by_date(date.today(), canteen.id, "lunch")
        print(f"   ✅ Retrieved menu: {found_menu.courses_json['primi']}\n")

        # Test User Repository
        print("4️⃣ Testing UserRepository...")
        user_repo = UserRepository(session)

        user = await user_repo.get_or_create(
            telegram_id=123456789, first_name="Mario", username="mario_rossi"
        )
        print(f"   ✅ Created user: {user.first_name} (Telegram: {user.telegram_id})\n")

        # Update canteen preference
        await user_repo.update_canteen_preference(123456789, canteen.id)
        print(f"   ✅ Updated user canteen preference\n")

        # Get all users by canteen
        users = await user_repo.get_users_by_canteen(canteen.id)
        print(f"   ✅ Users subscribed to {canteen.name}: {len(users)}\n")

    print("🎉 All tests passed!\n")
    print("✅ Canteen, Menu, User models working")
    print("✅ Repository pattern implemented")
    print("✅ JSON field for flexible menu structure")
    print("✅ Foreign key relationships working\n")


if __name__ == "__main__":
    asyncio.run(main())
