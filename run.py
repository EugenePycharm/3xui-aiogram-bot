import asyncio
import logging
from os import getenv
from dotenv import load_dotenv

load_dotenv()
TOKEN = getenv("BOT_TOKEN")

from aiogram import Bot, Dispatcher
from app.handlers import router

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        logging.basicConfig(level=logging.INFO)
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Stopping bot...')
