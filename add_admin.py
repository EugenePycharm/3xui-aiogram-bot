"""
Скрипт для добавления первого администратора.
Запуск: python add_admin.py <your_telegram_id>
"""
import asyncio
import sys
import os

from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from app.database.models import async_session, Admin
from sqlalchemy import select


async def add_admin(tg_id: int, username: str = None) -> None:
    """Добавить администратора."""
    async with async_session() as session:
        # Проверяем, существует ли уже
        existing = await session.scalar(select(Admin).where(Admin.tg_id == tg_id))
        if existing:
            print(f"Admin with ID {tg_id} already exists.")
            if existing.is_active:
                print("Status: ACTIVE")
            else:
                print("Status: INACTIVE")
                existing.is_active = True
                await session.commit()
                print("Admin activated.")
            return

        # Создаём нового
        admin = Admin(tg_id=tg_id, username=username)
        session.add(admin)
        await session.commit()

        print(f"Admin added successfully!")
        print(f"   Telegram ID: {tg_id}")
        print(f"   Username: @{username or 'not set'}")


async def list_admins() -> None:
    """Показать всех администраторов."""
    async with async_session() as session:
        admins = await session.execute(select(Admin))
        admins_list = admins.scalars().all()

        if not admins_list:
            print("No admins found.")
            return

        print(f"Admins ({len(admins_list)}):")
        for admin in admins_list:
            status = "[ACTIVE]" if admin.is_active else "[INACTIVE]"
            print(f"  {status} ID: {admin.tg_id} | @{admin.username or 'no username'}")


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python add_admin.py <telegram_id>  - add admin")
        print("  python add_admin.py list           - list all admins")
        print()
        print("Example:")
        print("  python add_admin.py 123456789")
        return

    command = sys.argv[1]

    if command == "list":
        await list_admins()
    else:
        try:
            tg_id = int(command)
            # Try to get username from argument
            username = sys.argv[2] if len(sys.argv) > 2 else None
            await add_admin(tg_id, username)
        except ValueError:
            print(f"Error: '{command}' is not a number.")
            print("Please enter a Telegram ID (number).")


if __name__ == "__main__":
    asyncio.run(main())
