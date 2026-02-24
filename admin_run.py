"""
Точка входа для запуска админ-бота.
"""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from app.database.models import create_tables, Admin
from app.database import requests as rq
from app.handlers.admin import router as admin_router
from app.middlewares.admin_auth import AdminAuthMiddleware

# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv("ADMIN_BOT_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

if not TOKEN:
    logging.error("Error: ADMIN_BOT_TOKEN not found in .env file.")
    sys.exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Подключаем роутер админ-бота
dp.include_router(admin_router)

# Добавляем middleware для проверки прав администратора
# Применяем после include_router для правильной работы
dp.message.middleware(AdminAuthMiddleware())
dp.callback_query.middleware(AdminAuthMiddleware())


async def main() -> None:
    """Основная функция запуска админ-бота."""
    # Настройка логирования
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logging.info("Starting VPN Admin Bot...")
    logging.info(f"Log level: {LOG_LEVEL}")

    await create_tables()

    bot_info = await bot.get_me()
    logging.info(f"Admin bot started as @{bot_info.username}")

    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Stopping admin bot...')
