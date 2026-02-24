"""
Хендлеры для поддержки пользователей.
"""
from aiogram import F, Router
from aiogram.types import Message

router = Router()


@router.message(F.text == '🆘 Поддержка')
async def support(message: Message) -> None:
    """
    Показ контактной информации поддержки.
    
    Args:
        message: Сообщение от пользователя
    """
    await message.answer(
        "По всем вопросам пишите: @blush_tp"
    )
