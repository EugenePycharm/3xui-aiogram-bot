from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text='👤 Профиль'), KeyboardButton(text='💳 Купить подписку')],
    [KeyboardButton(text='🆘 Поддержка')]
], resize_keyboard=True, input_field_placeholder='Выберите пункт меню:')

async def inline_plans(plans):
    keyboard = InlineKeyboardBuilder()
    for plan in plans:
        # Don't show trial plan in buy menu usually, but maybe for testing
        if plan.price > 0:
            keyboard.add(InlineKeyboardButton(text=f"{plan.name} - {plan.price} RUB", callback_data=f"buy_plan_{plan.id}"))
    return keyboard.adjust(1).as_markup()

async def profile_keyboard():
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="ref_link"))
    return keyboard.adjust(1).as_markup()