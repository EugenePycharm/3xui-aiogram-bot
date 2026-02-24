"""
Точка входа для запуска VPN бота.
"""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from app.database.models import create_tables
from app.handlers import router
from app.middlewares import CleanMessageMiddleware

# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

if not TOKEN:
    logging.error("Error: BOT_TOKEN not found in .env file.")
    sys.exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Подключение middleware для очистки сообщений
dp.message.middleware(CleanMessageMiddleware(max_messages=3))
dp.callback_query.middleware(CleanMessageMiddleware(max_messages=3))

# Подключение роутера
dp.include_router(router)


async def main() -> None:
    """Основная функция запуска бота."""
    # Настройка логирования
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    logging.info("Starting VPN User Bot...")
    logging.info(f"Log level: {LOG_LEVEL}")
    
    await create_tables()
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Stopping bot...')
