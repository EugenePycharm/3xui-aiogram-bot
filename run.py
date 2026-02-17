import asyncio
import logging
import os
from dotenv import load_dotenv

# Load .env from current directory
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("Error: BOT_TOKEN not found in .env file.")
    exit(1)

from aiogram import Bot, Dispatcher
from app.handlers import router
from app.database.models import create_tables

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main():
    await create_tables()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Stopping bot...')
