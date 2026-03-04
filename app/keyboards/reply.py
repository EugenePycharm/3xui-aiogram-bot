"""
Reply-клавиатуры для главного меню бота.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu() -> ReplyKeyboardMarkup:
    """
    Главное меню бота.

    Returns:
        ReplyKeyboardMarkup с кнопками меню
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="👤 Профиль"),
                KeyboardButton(text="💳 Купить подписку"),
            ],
            [KeyboardButton(text="🆘 Поддержка")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт меню:",
    )


# Готовый экземпляр клавиатуры
main_menu = get_main_menu()
