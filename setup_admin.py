"""
Скрипт для добавления первого администратора через запрос Telegram ID.
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.database.models import async_session, Admin
from sqlalchemy import select


async def get_my_id(bot_token: str) -> int:
    """Получить ID текущего пользователя через бота."""
    import aiohttp
    
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("ok"):
                    print(f"✅ Бот: @{data['result']['username']}")
                    return data["result"]["id"]
    return None


async def add_admin_interactive() -> None:
    """Интерактивное добавление админа."""
    print("=" * 50)
    print("🔧 Настройка админ-бота")
    print("=" * 50)
    print()
    
    # Получаем токен админ-бота
    admin_token = os.getenv("ADMIN_BOT_TOKEN")
    if not admin_token:
        print("❌ ADMIN_BOT_TOKEN не найден в .env")
        print("   Добавьте ADMIN_BOT_TOKEN=ваш_токен в файл .env")
        return
    
    print("1. Узнайте свой Telegram ID")
    print("   - Отправьте сообщение боту @userinfobot")
    print("   - Или используйте /getmyid в админ-боте (если есть)")
    print()
    
    try:
        tg_id = int(input("2. Введите ваш Telegram ID: ").strip())
    except ValueError:
        print("❌ Введите корректное число!")
        return
    
    username = input("3. Введите ваш username (необязательно, нажмите Enter для пропуска): ").strip()
    if username.startswith("@"):
        username = username[1:]
    
    async with async_session() as session:
        # Проверяем существующих
        existing = await session.scalar(select(Admin).where(Admin.tg_id == tg_id))
        
        if existing:
            print(f"\n⚠️ Администратор с ID {tg_id} уже существует.")
            if not existing.is_active:
                existing.is_active = True
                await session.commit()
                print("✅ Администратор активирован.")
            else:
                print("✅ Статус: активен")
            return
        
        # Создаём нового
        admin = Admin(tg_id=tg_id, username=username if username else None)
        session.add(admin)
        await session.commit()
        
        print("\n" + "=" * 50)
        print("✅ Администратор добавлен!")
        print("=" * 50)
        print(f"   Telegram ID: {tg_id}")
        print(f"   Username: @{username or 'не указан'}")
        print()
        print("📝 Теперь запустите админ-бота:")
        print("   python admin_run.py")
        print()
        print("   И отправьте /start в Telegram")


if __name__ == "__main__":
    asyncio.run(add_admin_interactive())
