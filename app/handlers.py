from aiogram.types import Message
from aiogram import Router
from aiogram.filters import CommandStart
from app.keyboards import main

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer('hi', reply_markup=main)
