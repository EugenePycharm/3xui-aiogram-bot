from aiogram.types import Message
from aiogram import Router, F
from aiogram.filters import CommandStart
from app.keyboards import main
import app.database.requests as rq

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await rq.add_user(tg_id=message.from_user.id, name=message.from_user.first_name, surname=message.from_user.last_name, user_tag=message.from_user.username)
    await message.answer('hi', reply_markup=main)
